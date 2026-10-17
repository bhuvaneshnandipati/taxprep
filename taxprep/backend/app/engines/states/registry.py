"""State engine registry. Every state engine exposes
compute(inp: StateInput, fed: FederalResult) -> StateResult."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

# States with no broad-based tax on wages for TY2025 (NH repealed its interest & dividends tax for 2025).
NO_INCOME_TAX = {"AK", "FL", "NV", "SD", "TN", "TX", "WA", "WY", "NH"}


@dataclass
class StateInput:
    state: str = "CA"
    withholding: float = 0.0
    full_year_resident: bool = True
    income_ratio: float = 1.0                 # legacy: share of income from the state (part-year/nonres)
    state_source_income: float | None = None  # preferred: dollars of state-source AGI (part-year/nonres)
    dependents: int = 0
    renter: bool = False
    itemized: float = 0.0                     # state itemized deductions (CA: excludes state income tax)
    fed_input: Any = None                     # FederalInput (needed for CA, which does not follow treaties)


@dataclass
class StateResult:
    state: str
    form: str
    lines: dict = field(default_factory=dict)
    explanations: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def refund(self):
        return self.lines.get("refund", 0.0)


def compute_state(inp: StateInput, fed) -> StateResult:
    code = (inp.state or "").upper()
    if code in NO_INCOME_TAX:
        return StateResult(state=code, form="none",
                           lines={"refund": 0.0, "withholding": float(round(inp.withholding))},
                           explanations=[f"{code} has no state income tax on wages — no state return required."])
    from . import california, newyork
    engines = {"CA": california.compute, "NY": newyork.compute}
    if code not in engines:
        raise ValueError(f"State {code} not yet supported. Supported: {sorted(engines)} "
                         f"+ no-tax states {sorted(NO_INCOME_TAX)}")
    return engines[code](inp, fed)
