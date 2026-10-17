"""Document upload + OCR extraction + review/apply into the return's income."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..db.models import TaxReturn, Document, AuditLog
from ..core.security import current_user_email
from ..ocr.service import process_upload
from ..schemas import IncomeIn
from pydantic import ValidationError
import math

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
    data = await file.read(MAX_BYTES + 1)
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
    if d.status == "applied":
        raise HTTPException(409, "Applied documents cannot be edited; change income directly instead")
    ex = dict(d.extracted)
    doc_type = corrections.pop("doc_type", None)
    if doc_type is not None:
        if doc_type not in ("W-2", "1099-INT", "1099-DIV", "1099-NEC"):
            raise HTTPException(400, "doc_type must be W-2, 1099-INT, 1099-DIV or 1099-NEC")
        d.doc_type = doc_type; ex["doc_type"] = doc_type
    for k, v in corrections.items():
        if k not in ("employer", "ein", "state"):
            try:
                v = float(str(v).replace(",", "").replace("$", "").strip() or 0)
            except ValueError:
                raise HTTPException(400, f"'{k}' must be a number")
        if isinstance(v, float) and (not math.isfinite(v) or v < 0):
            raise HTTPException(400, f"'{k}' must be a finite non-negative number")
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
    if d.status == "applied":
        raise HTTPException(409, "This document was already added to your return")
    f = {k: v["value"] for k, v in (d.extracted.get("fields") or {}).items()}
    inc = dict(r.income or {})
    if d.doc_type == "W-2":
        w2s = [w for w in (inc.get("w2s") or []) if any(w.get(k) for k in ("employer", "wages", "fed_withholding"))]
        w2s.append({"employer": f.get("employer", ""), "ein": f.get("ein", ""), "wages": f.get("wages", 0),
                    "fed_withholding": f.get("fed_withholding", 0), "ss_wages": f.get("ss_wages", 0),
                    "ss_tax": f.get("ss_tax", 0), "medicare_wages": f.get("medicare_wages"),
                    "medicare_tax": f.get("medicare_tax", 0), "state": f.get("state", ""),
                    "state_wages": f.get("state_wages", 0),
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
    try:
        inc = IncomeIn.model_validate(inc).model_dump()
    except ValidationError:
        raise HTTPException(422, "Review document values: income contains invalid amounts") from None
    r.income = inc; d.status = "applied"
    r.result_federal = {}; r.result_state = {}; r.status = "in_progress"
    db.commit()
    return {"ok": True, "income": inc}
