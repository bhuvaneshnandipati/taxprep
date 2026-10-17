"""New York: Form IT-201 (full-year resident) / IT-203 (nonresident or part-year resident).

NY starts from federal AGI, so federal treaty exclusions carry through (NY follows them).
IT-203 base tax is computed on all income as if a resident, then multiplied by the income
percentage (NY-source AGI / federal AGI).
"""
from .registry import StateInput, StateResult
from ..rules_loader import load_rules
from ..federal import marginal_tax, rnd


def ny_tax(ti: float, agi: float, fs: str, R: dict, warn: list) -> float:
    br = R["brackets"][fs]
    base = marginal_tax(ti, br)
    rc = R["recapture"]
    if agi <= rc["agi_start"]:
        return base
    # Tax benefit recapture (Tax Computation Worksheets): income in the first recapture tier is
    # taxed at the flat marginal rate, phased in over $50,000 of NY AGI.
    if ti <= rc["tier1_max_taxable"][fs]:
        flat = 0.0
        for lo, rate in br:
            if ti > lo:
                flat = rate
        full = ti * flat
        frac = min(1.0, (agi - rc["agi_start"]) / rc["phase_in"])
        return base + (full - base) * frac
    warn.append("NY tax benefit recapture for taxable income above "
                f"${rc['tier1_max_taxable'][fs]:,} is not computed — NY tax may be understated.")
    return base


def compute(inp: StateInput, fed) -> StateResult:
    R = load_rules("newyork")
    fs = fed.filing_status
    ex, warn = [], []
    fed_agi = float(fed.lines["agi"])
    std = R["standard_deduction"][fs]
    deduction = max(std, inp.itemized or 0.0)
    dep_ex = inp.dependents * R["dependent_exemption"]
    taxable = max(0.0, fed_agi - deduction - dep_ex)
    base_tax = ny_tax(taxable, fed_agi, fs, R, warn)
    if dep_ex:
        ex.append(f"NY dependent exemptions: ${dep_ex:,.0f} ({inp.dependents} x $1,000).")
    lines = {"federal_agi": fed_agi, "ny_agi": fed_agi, "deduction": deduction, "dependent_exemptions": dep_ex,
             "taxable_income": taxable}
    if inp.full_year_resident:
        tax = base_tax
        form = "IT-201"
        ex.append(f"IT-201: NY taxable income ${taxable:,.0f}; NY State tax ${tax:,.0f}.")
    else:
        if inp.state_source_income is not None:
            ny_src = max(0.0, inp.state_source_income)
        else:
            ny_src = fed_agi * max(0.0, min(1.0, inp.income_ratio))
            warn.append("IT-203 computed from an income percentage — enter NY-source income in dollars.")
        if ny_src > fed_agi:
            warn.append(f"NY-source income (${ny_src:,.0f}) cannot exceed federal AGI; limited to ${fed_agi:,.0f} "
                        f"(NY follows federal treaty exclusions).")
            ny_src = max(0.0, fed_agi)
        pct = 0.0 if fed_agi <= 0 else round(min(1.0, ny_src / fed_agi), 4)
        tax = base_tax * pct
        form = "IT-203"
        lines.update({"ny_source_income": ny_src, "base_tax": base_tax, "income_percentage": pct})
        ex.append(f"IT-203: base tax ${base_tax:,.0f} on all income x NY income percentage {pct:.2%} "
                  f"(NY-source ${ny_src:,.0f} / federal AGI ${fed_agi:,.0f}) = ${tax:,.0f}.")
    lines["tax"] = tax
    lines["total_tax"] = tax
    lines["withholding"] = inp.withholding
    lines["refund"] = inp.withholding - tax
    out = {k: (v if k == "income_percentage" else rnd(v)) for k, v in lines.items()}
    out["overpaid"] = max(0.0, out["refund"])
    out["owed"] = max(0.0, -out["refund"])
    warn.append("NYC / Yonkers local income tax, NY household credit and NY EITC are not computed.")
    return StateResult(state="NY", form=form, lines=out, explanations=ex, warnings=warn)
