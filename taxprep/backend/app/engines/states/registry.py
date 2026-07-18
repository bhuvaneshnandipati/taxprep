"""State engine registry. Every state engine exposes
compute(inp: StateInput, fed: FederalResult) -> StateResult."""
from dataclasses import dataclass, field

NO_INCOME_TAX = {"AK", "FL", "NV", "SD", "TN", "TX", "WA", "WY", "NH"}

@dataclass
class StateInput:
    state: str = "CA"
    withholding: float = 0.0
    full_year_resident: bool = True
    income_ratio: float = 1.0
    dependents: int = 0
    renter: bool = False

@dataclass
class StateResult:
    state: str
    form: str
    lines: dict = field(default_factory=dict)
    explanations: list = field(default_factory=list)

    @property
    def refund(self):
        return self.lines.get("refund", 0.0)

def compute_state(inp: StateInput, fed) -> StateResult:
    code = inp.state.upper()
    if code in NO_INCOME_TAX:
        return StateResult(state=code, form="none",
                           lines={"refund": inp.withholding},
                           explanations=[f"{code} has no state income tax on wages — no state return required."
                                         + (" NH taxes only interest/dividends for some years; verify if applicable." if code == "NH" else "")])
    from . import california, newyork
    engines = {"CA": california.compute, "NY": newyork.compute}
    if code not in engines:
        raise ValueError(f"State {code} not yet supported. Supported: {sorted(engines)} + no-tax states {sorted(NO_INCOME_TAX)}")
    return engines[code](inp, fed)
