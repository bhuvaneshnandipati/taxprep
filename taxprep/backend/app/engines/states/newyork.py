"""New York: Form IT-201 (full-year resident) / IT-203 (nonresident or part-year resident).

NY starts from federal AGI, so federal treaty exclusions carry through (NY follows them).
IT-203 base tax is computed on all income as if a resident, then multiplied by the income
percentage (NY-source AGI / federal AGI).
"""
from .registry import StateInput, StateResult
from ..rules_loader import load_rules
from ..federal import marginal_tax, rnd
import math


def _table(ti: float, rows: list, fs: str):
    """Published NYS/NYC tax table lookup (taxable income under $65,000)."""
    col = {"single": 2, "mfs": 2, "mfj": 3, "qss": 3, "hoh": 4}[fs]
    for r in rows:
        if r[0] <= ti < r[1]:
            return float(r[col])
    return None


def _schedule_whole_dollar(x: float, br: list) -> float:
    """Rate schedule with the published whole-dollar base amounts."""
    base = 0.0
    for i, (lo, rate) in enumerate(br):
        hi = br[i + 1][0] if i + 1 < len(br) else float("inf")
        if x <= hi:
            return base + (x - lo) * rate
        base = math.floor(base + (hi - lo) * rate + 0.5)
    return base


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
    T = load_rules("newyork_tables")
    tbl = _table(round(taxable), T["nys"], fs) if (taxable < 65000 and fed_agi <= R["recapture"]["agi_start"]) else None
    base_tax = tbl if tbl is not None else ny_tax(taxable, fed_agi, fs, R, warn)
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
    nys_net = tax
    city_tax = school_fixed = school_rr = yonkers = 0.0
    loc = (inp.locality or "").upper()
    if loc and not inp.full_year_resident:
        warn.append(f"Part-year {loc} residence (Form IT-360.1) is not computed; {loc} tax is left off.")
        loc = ""
    if loc == "NYC":
        ctbl = _table(round(taxable), T["nyc"], fs) if taxable < 65000 else None
        city_tax = ctbl if ctbl is not None else rnd(_schedule_whole_dollar(taxable, R["nyc_brackets"][fs]))
        ex.append(f"New York City resident tax on ${taxable:,.0f}: ${city_tax:,.0f}.")
        fx = R["nyc_school_credit_fixed"]
        if fed_agi <= fx["income_limit"]:
            school_fixed = fx[fs]
        rr = R["nyc_school_credit_rate_reduction"]
        if fed_agi <= rr["income_limit"]:
            fb = rr["first_bracket"][fs]
            school_rr = rnd(taxable * rr["rate_low"]) if taxable <= fb else rnd(rr["base"][fs] + (taxable - fb) * rr["rate_high"])
        ex.append(f"NYC school tax credits: ${school_fixed:,.0f} fixed + ${school_rr:,.0f} rate reduction (refundable).")
    elif loc == "YONKERS":
        yonkers = rnd(nys_net * R["yonkers_resident_rate"])
        ex.append(f"Yonkers resident surcharge 16.75% of NYS tax: ${yonkers:,.0f}.")
    lines.update({"nyc_tax": city_tax, "yonkers_tax": yonkers, "nyc_school_fixed": school_fixed,
                  "nyc_school_rr": school_rr, "local_withholding": inp.local_withholding, "locality": loc})
    tax = nys_net + city_tax + yonkers
    lines["total_tax"] = tax
    lines["withholding"] = inp.withholding
    payments = inp.withholding + inp.local_withholding + school_fixed + school_rr
    lines["total_payments"] = payments
    lines["refund"] = payments - tax
    out = {k: (v if k in ("income_percentage", "locality") else rnd(v)) for k, v in lines.items()}
    out["overpaid"] = max(0.0, out["refund"])
    out["owed"] = max(0.0, -out["refund"])
    if fed_agi <= R["household_credit_agi_limit"].get(fs if fs in ("single", "mfj") else "single", 0) or fed.lines.get("eitc"):
        warn.append("NY household credit and NY/NYC earned income credits (IT-215) are not computed; with low income "
                    "you may qualify for more refund.")
    return StateResult(state="NY", form=form, lines=out, explanations=ex, warnings=warn)
