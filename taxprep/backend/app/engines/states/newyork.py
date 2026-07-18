"""New York: Form IT-201 (resident) / IT-203 (nonresident, income-ratio prorated)."""
from .registry import StateInput, StateResult
from ..rules_loader import load_rules
from ..federal import marginal_tax

def compute(inp: StateInput, fed) -> StateResult:
    R = load_rules("newyork")
    fs = fed.filing_status
    ex = []
    ny_agi = float(fed.lines["11_agi"])
    std = R["standard_deduction"].get(fs, R["standard_deduction"]["single"])
    dep_ex = inp.dependents * R["dependent_exemption"]
    taxable = max(0.0, ny_agi - std - dep_ex)
    if dep_ex:
        ex.append(f"NY dependent exemptions: ${dep_ex:,.0f} ({inp.dependents} x $1,000).")
    tax = marginal_tax(taxable, R["brackets"][fs])
    if not inp.full_year_resident:
        ratio = max(0.0, min(1.0, inp.income_ratio))
        tax *= ratio
        ex.append(f"IT-203: tax prorated by NY-source income ratio {ratio:.0%}.")
    total_tax = tax
    refund = inp.withholding - total_tax
    r = lambda v: round(v)
    return StateResult(state="NY", form="IT-201" if inp.full_year_resident else "IT-203",
                       lines={"19_ny_agi": r(ny_agi), "34_deduction": r(std + dep_ex),
                              "37_taxable": r(taxable), "39_tax": r(tax),
                              "46_total_tax": r(total_tax), "72_withholding": r(inp.withholding),
                              "refund": r(refund)},
                       explanations=ex + ["NYC/Yonkers resident local tax not included; add locality in a later phase if applicable."])
