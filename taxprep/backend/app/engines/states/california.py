"""California: Form 540 / 540NR (delegates to the California engine)."""
from .registry import StateInput, StateResult
from ..california import compute_california, CAInput


def compute(inp: StateInput, fed) -> StateResult:
    ca = compute_california(CAInput(
        ca_withholding=inp.withholding, full_year_resident=inp.full_year_resident,
        ca_income_ratio=inp.income_ratio, ca_source_income=inp.state_source_income,
        dependents=inp.dependents, renter=inp.renter, itemized=inp.itemized,
        fed_input=inp.fed_input), fed)
    return StateResult(state="CA", form=ca.form, lines=ca.lines, explanations=ca.explanations,
                       warnings=ca.warnings)
