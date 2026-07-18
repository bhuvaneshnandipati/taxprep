from fastapi import APIRouter
from ..engines.interview import next_questions, progress
from ..engines.rules_loader import load_rules, available_years

router = APIRouter(prefix="/interview", tags=["interview"])

@router.post("/next")
def get_next(answers: dict):
    return {"next_questions": next_questions(answers), "progress": progress(answers)}

@router.get("/rules/years")
def years():
    return {"available_tax_years": available_years()}

@router.get("/rules/{pack}")
def rules(pack: str, year: int = 2025):
    return load_rules(pack, year)
