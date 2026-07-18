from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..db.models import User, TaxReturn
from ..core.security import current_user_email
from ..core.config import settings
from ..schemas import ProfileIn, IncomeIn, AnswersIn, TaxpayerIn
from ..engines.residency import determine_residency
from ..engines.federal import compute_federal, FederalInput
from ..engines.states.registry import compute_state, StateInput, NO_INCOME_TAX
from ..engines.interview import next_questions, progress

router = APIRouter(prefix="/returns", tags=["returns"])

def _user(db, email) -> User:
    u = db.query(User).filter_by(email=email).first()
    if not u:
        raise HTTPException(404, "User not found")
    return u

def _ret(db, email, rid) -> TaxReturn:
    r = db.query(TaxReturn).filter_by(id=rid).first()
    if not r or r.user.email != email:
        raise HTTPException(404, "Return not found")
    return r

@router.post("")
def create_return(email: str = Depends(current_user_email), db: Session = Depends(get_db)):
    r = TaxReturn(user_id=_user(db, email).id, tax_year=settings.DEFAULT_TAX_YEAR)
    db.add(r); db.commit(); db.refresh(r)
    return {"id": r.id, "tax_year": r.tax_year, "status": r.status}

@router.get("")
def list_returns(email: str = Depends(current_user_email), db: Session = Depends(get_db)):
    u = _user(db, email)
    return [{"id": r.id, "tax_year": r.tax_year, "status": r.status,
             "updated_at": str(r.updated_at)} for r in u.returns]

@router.put("/{rid}/profile")
def save_profile(rid: int, body: ProfileIn, email: str = Depends(current_user_email), db: Session = Depends(get_db)):
    r = _ret(db, email, rid)
    r.profile = body.model_dump(); db.commit()
    res = determine_residency(**{k: v for k, v in body.model_dump().items() if k not in ("country", "is_student")},
                              tax_year=r.tax_year)
    return {"residency": res.__dict__}

@router.put("/{rid}/answers")
def save_answers(rid: int, body: AnswersIn, email: str = Depends(current_user_email), db: Session = Depends(get_db)):
    r = _ret(db, email, rid)
    merged = dict(r.answers or {}); merged.update(body.answers)
    r.answers = merged; db.commit()
    return {"next_questions": next_questions(merged), "progress": progress(merged)}

@router.put("/{rid}/income")
def save_income(rid: int, body: IncomeIn, email: str = Depends(current_user_email), db: Session = Depends(get_db)):
    r = _ret(db, email, rid)
    r.income = body.model_dump(); db.commit()
    return {"ok": True}

@router.post("/{rid}/calculate")
def calculate(rid: int, email: str = Depends(current_user_email), db: Session = Depends(get_db)):
    r = _ret(db, email, rid)
    if not r.profile or not r.income:
        raise HTTPException(400, "Save profile and income before calculating")
    p, inc = r.profile, r.income
    res = determine_residency(citizen=p["citizen"], green_card=p["green_card"], visa=p["visa"],
                              first_entry_year=p["first_entry_year"], days_current=p["days_current"],
                              days_prior1=p["days_prior1"], days_prior2=p["days_prior2"], tax_year=r.tax_year)
    fin = FederalInput(
        filing_status=inc["filing_status"],
        wages=sum(w["wages"] for w in inc["w2s"]),
        fed_withholding=sum(w["fed_withholding"] for w in inc["w2s"]),
        interest=inc["interest"], dividends=inc["dividends"],
        qualified_dividends=inc["qualified_dividends"],
        capital_gain_lt=inc["capital_gain_lt"], capital_gain_st=inc["capital_gain_st"],
        se_income=inc["se_income"], scholarship_taxable=inc["scholarship_taxable"],
        student_loan_interest=inc["student_loan_interest"], itemized=inc["itemized"],
        qualifying_children=inc["qualifying_children"], other_dependents=inc["other_dependents"],
        tuition_paid=inc["tuition_paid"], education_credit_type=inc["education_credit_type"],
        country=p.get("country", ""), is_student=p.get("is_student", False),
        estimated_payments=inc["estimated_payments"])
    fed = compute_federal(fin, res)
    try:
        ca = compute_state(StateInput(
            state=inc.get("state", "CA"),
            withholding=sum(w["state_withholding"] for w in inc["w2s"]),
            full_year_resident=inc["ca_full_year_resident"],
            income_ratio=inc["ca_income_ratio"],
            dependents=inc["qualifying_children"] + inc["other_dependents"],
            renter=inc["ca_renter"]), fed)
    except ValueError as e:
        raise HTTPException(400, str(e))
    out = {
        "residency": res.__dict__,
        "federal": {"form": fed.form, "filing_status": fed.filing_status,
                    "lines": fed.lines, "explanations": fed.explanations, "treaty": fed.treaty},
        "state": {"state": getattr(ca, "state", "CA"), "form": ca.form,
                  "lines": ca.lines, "explanations": ca.explanations},
        "checklist": build_checklist(res, fed, ca),
    }
    r.result_federal = out["federal"]; r.result_state = out["state"]; r.status = "complete"
    db.commit()
    return out

def build_checklist(res, fed, ca):
    items = [f"Form {fed.form} — U.S. Individual Income Tax Return"]
    if fed.lines.get("10_adjustments"):
        items.append("Schedule 1 — Adjustments to income")
    if fed.lines.get("2b_interest", 0) + fed.lines.get("3b_dividends", 0) > 1500:
        items.append("Schedule B — Interest and Ordinary Dividends")
    if fed.lines.get("7_capital_gain"):
        items += ["Schedule D — Capital Gains and Losses", "Form 8949 — Sales of Capital Assets"]
    if fed.lines.get("23_other_taxes"):
        items.append("Schedule 2 — Additional Taxes")
    if res.form_8843_required:
        items.append("Form 8843 — Statement for Exempt Individuals")
    if fed.treaty and fed.treaty.get("form_8833_required"):
        items.append("Form 8833 — Treaty-Based Return Position Disclosure")
    if ca.form != "none":
        state_name = {"CA": "California", "NY": "New York"}.get(getattr(ca, "state", "CA"), getattr(ca, "state", ""))
        items.append(f"{state_name} Form {ca.form}")
        items.append("Attach Copy B of each W-2 to the federal return; Copy 2 to the state return")
    else:
        items.append("No state income tax return required")
    return items


@router.put("/{rid}/taxpayer")
def save_taxpayer(rid: int, body: TaxpayerIn, email: str = Depends(current_user_email), db: Session = Depends(get_db)):
    r = _ret(db, email, rid)
    prof = dict(r.profile or {}); prof["taxpayer"] = body.model_dump()
    r.profile = prof; db.commit()
    return {"ok": True}


@router.get("/{rid}/package.pdf")
def download_package(rid: int, email: str = Depends(current_user_email), db: Session = Depends(get_db)):
    from ..pdf.forms import build_package
    r = _ret(db, email, rid)
    if not r.result_federal:
        raise HTTPException(400, "Run /calculate before downloading the package")
    result = {"federal": r.result_federal, "state": r.result_state,
              "residency": _residency_dict(r), "checklist": build_checklist_saved(r)}
    taxpayer = (r.profile or {}).get("taxpayer", {})
    taxpayer.setdefault("country", (r.profile or {}).get("country", ""))
    pdf = build_package(taxpayer, r.profile or {}, result, year=r.tax_year)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="filing-package-{r.tax_year}.pdf"'})


def _residency_dict(r):
    p = r.profile or {}
    res = determine_residency(citizen=p.get("citizen", False), green_card=p.get("green_card", False),
                              visa=p.get("visa", ""), first_entry_year=p.get("first_entry_year", 0),
                              days_current=p.get("days_current", 0), days_prior1=p.get("days_prior1", 0),
                              days_prior2=p.get("days_prior2", 0), tax_year=r.tax_year)
    return res.__dict__


def build_checklist_saved(r):
    class _F:  # lightweight adapters over saved JSON
        form = r.result_federal["form"]; lines = r.result_federal["lines"]; treaty = r.result_federal.get("treaty")
    class _C:
        form = r.result_state["form"]; lines = r.result_state["lines"]; state = r.result_state.get("state", "CA")
    class _R:
        form_8843_required = _residency_dict(r)["form_8843_required"]
    return build_checklist(_R, _F, _C)
