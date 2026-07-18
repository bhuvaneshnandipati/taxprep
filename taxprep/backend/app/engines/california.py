"""California engine: Form 540 (resident) and 540NR (part-year/nonresident)."""
from dataclasses import dataclass, field
from .rules_loader import load_rules
from .federal import FederalResult, marginal_tax

@dataclass
class CAInput:
    ca_withholding: float = 0.0
    full_year_resident: bool = True
    ca_income_ratio: float = 1.0
    dependents: int = 0
    renter: bool = False

@dataclass
class CAResult:
    form: str
    lines: dict = field(default_factory=dict)
    explanations: list = field(default_factory=list)

    @property
    def refund(self):
        return self.lines.get("refund", 0.0)

def compute_california(inp: CAInput, fed: FederalResult) -> CAResult:
    R = load_rules("california")
    fs = fed.filing_status
    ex = []
    ca_agi = float(fed.lines["11_agi"])  # v1: conformity; Sch CA adjustments in phase 5
    std = R["standard_deduction"].get(fs, R["standard_deduction"]["single"])
    taxable = max(0.0, ca_agi - std)
    tax = marginal_tax(taxable, R["brackets"][fs])
    if taxable > R["mental_health_tax"]["threshold"]:
        mh = (taxable - R["mental_health_tax"]["threshold"]) * R["mental_health_tax"]["rate"]
        tax += mh
        ex.append(f"Mental Health Services Tax (1% over $1M): ${mh:,.0f}.")
    if not inp.full_year_resident:
        tax *= max(0.0, min(1.0, inp.ca_income_ratio))
        ex.append(f"540NR: tax prorated by CA-source ratio {inp.ca_income_ratio:.0%}.")

    n_personal = 2 if fs in ("mfj", "qss") else 1
    excred = n_personal * R["exemption_credit"]["personal"] + inp.dependents * R["exemption_credit"]["dependent"]
    if ca_agi > R["exemption_phaseout_agi"][fs]:
        excred = 0.0
        ex.append("Exemption credits phased out (high AGI).")

    renters = 0.0
    rc = R["renters_credit"]
    if inp.renter:
        limit = rc["agi_limit_mfj"] if fs in ("mfj", "qss", "hoh") else rc["agi_limit_single"]
        if ca_agi <= limit:
            renters = rc["mfj"] if fs in ("mfj", "qss", "hoh") else rc["single"]
            ex.append(f"Nonrefundable renter's credit: ${renters:,.0f}.")

    total_tax = max(0.0, tax - excred - renters)
    refund = inp.ca_withholding - total_tax
    r = lambda v: round(v)
    lines = {"17_ca_agi": r(ca_agi), "18_deduction": r(std), "19_taxable": r(taxable),
             "31_tax": r(tax), "32_exemption_credits": r(min(excred + renters, tax)),
             "64_total_tax": r(total_tax), "71_withholding": r(inp.ca_withholding),
             "refund": r(refund)}
    return CAResult(form="540" if inp.full_year_resident else "540NR", lines=lines, explanations=ex)
