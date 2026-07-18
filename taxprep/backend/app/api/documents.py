"""Document upload + OCR extraction + review/apply into the return's income."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..db.models import TaxReturn, Document, AuditLog
from ..core.security import current_user_email
from ..ocr.service import process_upload

router = APIRouter(prefix="/returns/{rid}/documents", tags=["documents"])
ALLOWED = (".pdf", ".jpg", ".jpeg", ".png", ".heic")
MAX_BYTES = 15 * 1024 * 1024

def _ret(db, email, rid) -> TaxReturn:
    r = db.query(TaxReturn).filter_by(id=rid).first()
    if not r or r.user.email != email:
        raise HTTPException(404, "Return not found")
    return r

@router.post("")
async def upload(rid: int, file: UploadFile = File(...),
                 email: str = Depends(current_user_email), db: Session = Depends(get_db)):
    r = _ret(db, email, rid)
    if not file.filename or not file.filename.lower().endswith(ALLOWED):
        raise HTTPException(400, f"Unsupported file type. Allowed: {', '.join(ALLOWED)}")
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(400, "File too large (max 15 MB)")
    try:
        extracted = process_upload(data, file.filename)
    except Exception:
        raise HTTPException(422, "Could not read this document. Try a clearer photo or enter values manually.")
    doc = Document(return_id=r.id, filename=file.filename,
                   doc_type=extracted["doc_type"], extracted=extracted)
    db.add(doc)
    db.add(AuditLog(user_email=email, action="document_upload", detail=file.filename))
    db.commit(); db.refresh(doc)
    return {"id": doc.id, "doc_type": doc.doc_type, "extracted": extracted}

@router.get("")
def list_docs(rid: int, email: str = Depends(current_user_email), db: Session = Depends(get_db)):
    r = _ret(db, email, rid)
    return [{"id": d.id, "filename": d.filename, "doc_type": d.doc_type,
             "status": d.status, "extracted": d.extracted} for d in
            db.query(Document).filter_by(return_id=r.id).all()]

@router.put("/{doc_id}")
def review(rid: int, doc_id: int, corrections: dict,
           email: str = Depends(current_user_email), db: Session = Depends(get_db)):
    """User-reviewed field corrections: {field: value}."""
    r = _ret(db, email, rid)
    d = db.query(Document).filter_by(id=doc_id, return_id=r.id).first()
    if not d:
        raise HTTPException(404, "Document not found")
    ex = dict(d.extracted)
    for k, v in corrections.items():
        ex.setdefault("fields", {})[k] = {"value": v, "confidence": 1.0, "raw": "user-corrected"}
    ex["needs_review"] = False
    d.extracted = ex; d.status = "reviewed"; db.commit()
    return {"ok": True, "extracted": ex}

@router.post("/{doc_id}/apply")
def apply_to_return(rid: int, doc_id: int,
                    email: str = Depends(current_user_email), db: Session = Depends(get_db)):
    """Merge extracted values into the return's income."""
    r = _ret(db, email, rid)
    d = db.query(Document).filter_by(id=doc_id, return_id=r.id).first()
    if not d:
        raise HTTPException(404, "Document not found")
    f = {k: v["value"] for k, v in (d.extracted.get("fields") or {}).items()}
    inc = dict(r.income or {})
    if d.doc_type == "W-2":
        w2s = list(inc.get("w2s") or [])
        w2s.append({"employer": f.get("employer", ""), "wages": f.get("wages", 0),
                    "fed_withholding": f.get("fed_withholding", 0),
                    "state_withholding": f.get("state_withholding", 0)})
        inc["w2s"] = w2s
    elif d.doc_type == "1099-INT":
        inc["interest"] = (inc.get("interest") or 0) + f.get("interest", 0)
    elif d.doc_type == "1099-DIV":
        inc["dividends"] = (inc.get("dividends") or 0) + f.get("dividends", 0)
    elif d.doc_type == "1099-NEC":
        inc["se_income"] = (inc.get("se_income") or 0) + f.get("nonemployee_comp", 0)
    else:
        raise HTTPException(400, "Unknown document type — review and set the type first")
    r.income = inc; d.status = "applied"; db.commit()
    return {"ok": True, "income": inc}
