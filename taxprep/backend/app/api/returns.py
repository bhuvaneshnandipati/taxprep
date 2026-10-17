from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..db.models import User, TaxReturn, Document, AuditLog
from ..core.security import current_user_email
from ..core.config import settings
from ..schemas import ProfileIn, IncomeIn, AnswersIn, TaxpayerIn
from ..engines.residency import determine_residency, EXEMPT_VISAS
from ..engines.federal import compute_federal, FederalInput
from ..engines.states.registry import compute_state, StateInput
from ..engines.interview import next_questions, progress
from ..engines.rules_loader import load_rules
from ..core.crypto import protect, reveal

router = APIRouter(prefix="/returns", tags=["returns"])

PROFILE_KEYS = ("citizen", "green_card", "visa", "first_entry_year", "days_current", "days_prior1",
                "days_prior2", "exempt_days_current", "exempt_days_prior1", "exempt_days_prior2",
                "prior_exempt_years", "first_nonexempt_day")


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


def residency_for(profile: dict, tax_year: int):
    p = profile or {}
    return determine_residency(**{k: p[k] for k in PROFILE_KEYS if k in p}, tax_year=tax_year)


def _profile_answers(p: dict, status: str) -> dict:
    """Server-side answers derived from the profile so the interview never re-asks them."""
    return {"citizen": "yes" if p.get("citizen") else "no",
            "green_card": "yes" if p.get("green_card") else "no",
            "is_student": "yes" if p.get("is_student") else "no",
            "_residency": status}


@router.post("")
def create_return(email: str = Depends(current_user_email), db: Session = Depends(get_db)):
    r = TaxReturn(user_id=_user(db, email).id, tax_year=settings.DEFAULT_TAX_YEAR)
    db.add(r); db.commit(); db.refresh(r)
    return {"id": r.id, "tax_year": r.tax_year, "status": r.status}


@router.get("")
def list_returns(email: str = Depends(current_user_email), db: Session = Depends(get_db)):
    u = _user(db, email)
    return [{"id": r.id, "tax_year": r.tax_year, "status": r.status,
             "name": " ".join(filter(None, [((r.profile or {}).get("taxpayer") or {}).get("first_name", ""),
                                            ((r.profile or {}).get("taxpayer") or {}).get("last_name", "")])),
             "updated_at": str(r.updated_at)} for r in u.returns]


@router.get("/{rid}")
def get_return(rid: int, email: str = Depends(current_user_email), db: Session = Depends(get_db)):
    """Everything the wizard needs to resume a saved return."""
    r = _ret(db, email, rid)
    prof = reveal(dict(r.profile or {}))
    taxpayer = reveal(prof.pop("taxpayer", {}))
    out = {"id": r.id, "tax_year": r.tax_year, "status": r.status, "taxpayer": taxpayer,
           "profile": prof or None, "answers": r.answers or {}, "income": r.income or None,
           "residency": None, "next_questions": next_questions(r.answers or {}),
           "progress": progress(r.answers or {}), "result": None}
    if prof:
        out["residency"] = residency_for(prof, r.tax_year).to_dict()
    if r.result_federal and "agi" in (r.result_federal.get("lines") or {}):   # skip pre-v2 results
        out["result"] = {"federal": r.result_federal, "state": r.result_state,
                         "residency": out["residency"],
                         "checklist": (r.result_federal or {}).get("_checklist", []),
                         "mailing": (r.result_federal or {}).get("_mailing", {})}
    return out


@router.delete("/{rid}")
def delete_return(rid: int, email: str = Depends(current_user_email), db: Session = Depends(get_db)):
    r = _ret(db, email, rid)
    db.query(Document).filter_by(return_id=r.id).delete()
    db.delete(r)
    db.add(AuditLog(user_email=email, action="return_delete", detail=str(rid)))
    db.commit()
    return {"ok": True}


@router.put("/{rid}/profile")
def save_profile(rid: int, body: ProfileIn, email: str = Depends(current_user_email), db: Session = Depends(get_db)):
    r = _ret(db, email, rid)
    prof = dict(r.profile or {})
    prof.update(protect(body.model_dump()))
    r.profile = prof
    res = residency_for(prof, r.tax_year)
    merged = dict(r.answers or {}); merged.update(_profile_answers(prof, res.status))
    r.answers = merged
    _invalidate(r)
    db.commit()
    return {"residency": res.to_dict(), "next_questions": next_questions(merged), "progress": progress(merged)}


@router.put("/{rid}/answers")
def save_answers(rid: int, body: AnswersIn, email: str = Depends(current_user_email), db: Session = Depends(get_db)):
    r = _ret(db, email, rid)
    merged = dict(r.answers or {})
    merged.update({k: v for k, v in body.answers.items() if not str(k).startswith("_")})
    if r.profile:   # residency is decided by the server, never by the client
        merged.update(_profile_answers(r.profile, residency_for(r.profile, r.tax_year).status))
    r.answers = merged; db.commit()
    return {"next_questions": next_questions(merged), "progress": progress(merged)}


@router.put("/{rid}/income")
def save_income(rid: int, body: IncomeIn, email: str = Depends(current_user_email), db: Session = Depends(get_db)):
    r = _ret(db, email, rid)
    r.income = body.model_dump()
    _invalidate(r)
    db.commit()
    return {"ok": True}


@router.put("/{rid}/taxpayer")
def save_taxpayer(rid: int, body: TaxpayerIn, email: str = Depends(current_user_email), db: Session = Depends(get_db)):
    r = _ret(db, email, rid)
    prof = dict(r.profile or {}); prof["taxpayer"] = protect(body.model_dump())
    r.profile = prof; db.commit()
    return {"ok": True}


def _invalidate(r: TaxReturn):
    if r.result_federal:
        r.result_federal = {}; r.result_state = {}; r.status = "in_progress"


def run_calculation(r: TaxReturn) -> dict:
    p = r.profile or {}
    inc = IncomeIn(**(r.income or {})).model_dump()
    res = residency_for(p, r.tax_year)
    if res.status == "dual_status" and any(inc[k] for k in ("interest", "dividends", "capital_gain_lt", "capital_gain_st")):
        raise ValueError("Dual-status investment income requires period-specific NIIT calculations not supported here.")
    w2s = inc["w2s"]
    state = (inc.get("state") or "CA").upper()
    state_wh = sum(w["state_withholding"] for w in w2s if (w.get("state") or state).upper() == state)
    all_state_tax = sum(w["state_withholding"] for w in w2s) + inc["state_tax_other"]
    med = [w["medicare_wages"] if w["medicare_wages"] is not None else w["wages"] for w in w2s]
    # Fail closed for known unsupported credits/deductions rather than return a wrong refund.
    if inc["age"] >= 65:
        raise ValueError("Age 65+ deductions are not supported in this preview; calculation is blocked.")
    if inc["education_credit_type"] == "aotc" and inc["tuition_paid"] and inc["age"] < 24:
        raise ValueError("AOTC eligibility under age 24 requires additional support/parent information not supported here.")
    if any(w["medicare_tax"] > med[i] * 0.0145 + 1 for i, w in enumerate(w2s)):
        raise ValueError("Additional Medicare withholding credit is not supported; calculation is blocked.")
    if sum(w["ss_tax"] for w in w2s) > 176100 * 0.062 + 1:
        raise ValueError("Excess Social Security withholding credit is not supported; calculation is blocked.")
    fin = FederalInput(
        filing_status=inc["filing_status"],
        wages=sum(w["wages"] for w in w2s),
        medicare_wages=sum(med),
        fed_withholding=sum(w["fed_withholding"] for w in w2s) + inc["withholding_1099"],
        wages_nr_period=inc["wages_nr_period"],
        comp_1042s=inc["comp_1042s"], scholarship_1042s=inc["scholarship_1042s"],
        withholding_1042s=inc["withholding_1042s"],
        interest=inc["interest"], dividends=inc["dividends"],
        qualified_dividends=inc["qualified_dividends"],
        capital_gain_lt=inc["capital_gain_lt"], capital_gain_st=inc["capital_gain_st"],
        se_income=inc["se_income"], scholarship_taxable=inc["scholarship_taxable"],
        student_loan_interest=inc["student_loan_interest"], itemized=inc["itemized"],
        state_income_tax_paid=all_state_tax, charitable=inc["charitable"],
        other_itemized=inc["other_itemized"], qualified_tips=inc["qualified_tips"],
        qualified_overtime=inc["qualified_overtime"], has_ssn=inc["has_ssn"], age=inc["age"],
        qualifying_children=inc["qualifying_children"], other_dependents=inc["other_dependents"],
        tuition_paid=inc["tuition_paid"], education_credit_type=inc["education_credit_type"],
        country=p.get("country", ""), is_student=p.get("is_student", False),
        days_present=p.get("days_current", 0), first_entry_year=p.get("first_entry_year", 0),
        estimated_payments=inc["estimated_payments"])
    fed = compute_federal(fin, res)
    st = compute_state(StateInput(
        state=state, withholding=state_wh, full_year_resident=inc["ca_full_year_resident"],
        income_ratio=inc["ca_income_ratio"], state_source_income=inc["state_source_income"],
        dependents=inc["qualifying_children"] + inc["other_dependents"], renter=inc["ca_renter"],
        itemized=inc["state_itemized"], fed_input=fin), fed)

    fica_paid = sum(w["ss_tax"] + w["medicare_tax"] for w in w2s)
    fica_note = (res.status == "nonresident" and res.exempt_days_current > 0
                 and p.get("visa") in EXEMPT_VISAS and fica_paid > 0)
    checklist = build_checklist(res, fed, st, fica_note, fica_paid)
    mailing = mailing_for(fed, st, (p.get("taxpayer") or {}).get("state") or state)
    federal = {"form": fed.form, "mode": fed.mode, "filing_status": fed.filing_status, "lines": fed.lines,
               "explanations": fed.explanations, "warnings": fed.warnings, "treaty": fed.treaty,
               "schedules": fed.schedules}
    state_out = {"state": st.state, "form": st.form, "lines": st.lines, "explanations": st.explanations,
                 "warnings": st.warnings}
    if fica_note:
        federal["warnings"] = federal["warnings"] + [
            f"Your W-2s show ${fica_paid:,.2f} of Social Security/Medicare tax. F/J/M students who are "
            f"nonresident aliens are exempt — ask your employer for a refund first; if they refuse, file "
            f"Form 843 with Form 8316."]
    from ..engines.rules_loader import load_rules as _lr
    std = 0.0
    if st.form != "none" and state in ("CA", "NY"):
        std = _lr("california" if state == "CA" else "newyork")["standard_deduction"][fed.filing_status]
    return {"residency": res.to_dict(), "federal": federal, "state": state_out,
            "checklist": checklist, "mailing": mailing,
            "_dependents": inc["qualifying_children"] + inc["other_dependents"],
            "_state_wages": sum(w["state_wages"] or w["wages"] for w in w2s if (w.get("state") or state).upper() == state),
            "_state_std": std, "_wages_nr_period": inc["wages_nr_period"]}


@router.post("/{rid}/calculate")
def calculate(rid: int, email: str = Depends(current_user_email), db: Session = Depends(get_db)):
    r = _ret(db, email, rid)
    if not r.profile or not r.income:
        raise HTTPException(400, "Save your residency profile and income before calculating")
    try:
        out = run_calculation(r)
    except ValueError as e:
        raise HTTPException(400, str(e))
    r.result_federal = dict(out["federal"], _checklist=out["checklist"], _mailing=out["mailing"])
    r.result_state = out["state"]; r.status = "complete"
    db.commit()
    return {k: v for k, v in out.items() if not k.startswith("_")}


def mailing_for(fed, st, home_state: str) -> dict:
    M = load_rules("mailing")
    owe = fed.lines.get("refund", 0) < 0
    f = M["federal"].get(fed.form)
    if fed.form == "1040":
        f = f.get((home_state or "").upper()) or f["default"]
    fed_addr = f if isinstance(f, str) else f["payment" if owe else "no_payment"]
    out = {"federal": fed_addr}
    if st.form != "none" and st.state in M["state"]:
        out["state"] = M["state"][st.state]["payment" if st.lines.get("refund", 0) < 0 else "no_payment"]
    return out


def build_checklist(res, fed, st, fica_note=False, fica_paid=0.0):
    titles = {"1040-NR": "Form 1040-NR — U.S. Nonresident Alien Income Tax Return",
              "1040": "Form 1040 — U.S. Individual Income Tax Return",
              "1040 (Dual-Status)": "Form 1040 marked \"Dual-Status Return\" (resident period + total tax)"}
    items = [titles.get(fed.form, f"Form {fed.form}")]
    items += [s for s in fed.schedules]
    if res.form_8843_required:
        items.append("Form 8843 — Statement for Exempt Individuals (one per person, incl. dependents on F-2/J-2)")
    if fica_note:
        items.append(f"Ask employer to refund ${fica_paid:,.2f} FICA; else Form 843 + Form 8316")
    items.append("Attach Copy B of every W-2 (and 1042-S) to the front of the federal return")
    if st.form != "none":
        name = {"CA": "California", "NY": "New York"}.get(st.state, st.state)
        items.append(f"{name} Form {st.form}" + (" + Schedule CA (540NR)" if st.form == "540NR" else ""))
        items.append(f"Attach Copy 2 of each W-2 to the {name} return")
    else:
        items.append("No state income tax return required")
    items.append("Sign and date every return — unsigned returns are not processed")
    return list(dict.fromkeys(items))


@router.get("/{rid}/package.pdf")
def download_package(rid: int, email: str = Depends(current_user_email), db: Session = Depends(get_db)):
    from ..pdf.forms import build_package
    r = _ret(db, email, rid)
    if not r.result_federal:
        raise HTTPException(400, "Calculate your return before downloading the filing package")
    result = run_calculation(r)          # always rebuild from saved inputs so PDF == current rules
    profile = reveal(dict(r.profile or {}))
    taxpayer = reveal(dict(profile.get("taxpayer", {})))
    try:
        pdf = build_package(taxpayer, profile, result, year=r.tax_year)
    except FileNotFoundError as e:
        raise HTTPException(500, f"Form template missing on the server: {e}")
    db.add(AuditLog(user_email=email, action="package_download", detail=str(rid))); db.commit()
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="tax-return-{r.tax_year}.pdf"'})
