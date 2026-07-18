"""Admin panel API: users, audit log, OCR review queue, rules management."""
import os, pathlib, yaml
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..db.models import User, AuditLog, Document
from ..core.security import current_user_email
from ..engines.rules_loader import RULES_DIR, load_rules, available_years
from ..core.retention import purge_audit_log, AUDIT_RETENTION_MONTHS

router = APIRouter(prefix="/admin", tags=["admin"])

def require_admin(email: str = Depends(current_user_email), db: Session = Depends(get_db)) -> User:
    u = db.query(User).filter_by(email=email).first()
    bootstrap = email in [e.strip() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()]
    if not u or (u.role != "admin" and not bootstrap):
        raise HTTPException(403, "Admin access required")
    if bootstrap and u.role != "admin":
        u.role = "admin"; db.commit()
    return u

@router.get("/users")
def users(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return [{"id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role,
             "returns": len(u.returns), "created_at": str(u.created_at)} for u in db.query(User).all()]

@router.put("/users/{uid}/role")
def set_role(uid: int, body: dict, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    role = body.get("role")
    if role not in ("user", "admin"):
        raise HTTPException(400, "role must be 'user' or 'admin'")
    u = db.query(User).filter_by(id=uid).first()
    if not u:
        raise HTTPException(404, "User not found")
    u.role = role
    db.add(AuditLog(user_email=admin.email, action="set_role", detail=f"{u.email} -> {role}"))
    db.commit()
    return {"ok": True}

@router.get("/audit")
def audit(limit: int = 100, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    purge_audit_log(db)  # opportunistic cleanup — keeps retention hands-off
    rows = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(limit).all()
    return {"retention_months": AUDIT_RETENTION_MONTHS,
            "entries": [{"at": str(a.at), "user": a.user_email, "action": a.action, "detail": a.detail} for a in rows]}

@router.post("/audit/purge")
def audit_purge(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    deleted = purge_audit_log(db)
    db.add(AuditLog(user_email=admin.email, action="audit_purge", detail=f"removed {deleted} entries older than {AUDIT_RETENTION_MONTHS} months"))
    db.commit()
    return {"deleted": deleted}

@router.get("/documents/review-queue")
def review_queue(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    docs = db.query(Document).filter(Document.status == "extracted").all()
    return [{"id": d.id, "return_id": d.return_id, "filename": d.filename,
             "doc_type": d.doc_type,
             "low_confidence_fields": (d.extracted or {}).get("low_confidence_fields", []),
             "needs_review": (d.extracted or {}).get("needs_review", False)} for d in docs
            if (d.extracted or {}).get("needs_review")]

@router.get("/rules")
def list_rules(admin: User = Depends(require_admin)):
    out = {}
    for y in available_years():
        out[y] = sorted(p.stem for p in (RULES_DIR / str(y)).glob("*.yaml"))
    return out

@router.get("/rules/{year}/{pack}")
def get_pack(year: int, pack: str, admin: User = Depends(require_admin)):
    return load_rules(pack, year)

@router.put("/rules/{year}/{pack}")
def update_pack(year: int, pack: str, body: dict,
                admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Replace a rule pack. Previous version saved as .bak; cache cleared."""
    path = RULES_DIR / str(year) / f"{pack}.yaml"
    if not path.exists():
        raise HTTPException(404, f"No pack '{pack}' for {year}")
    if not isinstance(body, dict) or body.get("year") != year:
        raise HTTPException(400, "Pack payload must be an object with matching 'year'")
    path.with_suffix(".yaml.bak").write_text(path.read_text())
    path.write_text(yaml.safe_dump(body, sort_keys=False))
    load_rules.cache_clear()
    db.add(AuditLog(user_email=admin.email, action="rules_update", detail=f"{year}/{pack}"))
    db.commit()
    return {"ok": True, "backup": str(path.with_suffix('.yaml.bak').name)}
