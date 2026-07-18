"""California: Form 540 / 540NR (delegates to the existing engine)."""
from .registry import StateInput, StateResult
from ..california import compute_california, CAInput

def compute(inp: StateInput, fed) -> StateResult:
    ca = compute_california(CAInput(
        ca_withholding=inp.withholding, full_year_resident=inp.full_year_resident,
        ca_income_ratio=inp.income_ratio, dependents=inp.dependents, renter=inp.renter), fed)
    return StateResult(state="CA", form=ca.form, lines=ca.lines, explanations=ca.explanations)
