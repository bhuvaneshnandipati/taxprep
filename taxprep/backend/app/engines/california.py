"""California engine: Form 540 (full-year resident) and 540NR (part-year resident / nonresident).

California does not follow U.S. tax treaties and taxes residents on worldwide income, so the CA
starting point is rebuilt from the raw income inputs (treaty-exempt wages and scholarships,
and the bank interest / capital gains that a federal nonresident alien leaves off Form 1040-NR,
are all California income for a California resident).
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from .rules_loader import load_rules
from .federal import FederalResult, marginal_tax, rnd


@dataclass
class CAInput:
    ca_withholding: float = 0.0
    full_year_resident: bool = True
    ca_income_ratio: float = 1.0
    ca_source_income: float | None = None
    dependents: int = 0
    renter: bool = False
    itemized: float = 0.0
    fed_input: object = None


@dataclass
class CAResult:
    form: str
    lines: dict = field(default_factory=dict)
    explanations: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def refund(self):
        return self.lines.get("refund", 0.0)


def ca_tax(ti: float, fs: str, R: dict) -> float:
    if ti <= 0:
        return 0.0
    t = marginal_tax(ti, R["brackets"][fs])
    mh = R["mental_health_tax"]
    if ti > mh["threshold"]:
        t += (ti - mh["threshold"]) * mh["rate"]
    return t


def _ca_total_agi(fed: FederalResult, fi) -> tuple[float, list]:
    """California AGI on a worldwide basis, ignoring federal treaty exclusions."""
    ex = []
    L = fed.lines
    if fi is None:                       # no raw inputs: fall back to federal AGI + treaty add-back
        add = L.get("treaty_exempt_income", 0.0)
        if add:
            ex.append(f"Treaty-exempt income ${add:,.0f} added back: California does not follow tax treaties.")
        return float(L.get("agi", 0.0)) + add, ex
    fs = fed.filing_status
    cl = load_rules("federal")["capital_loss_limit"][fs]
    net_cg = fi.capital_gain_st + fi.capital_gain_lt
    cg = net_cg if net_cg >= 0 else max(net_cg, -cl)
    wages = fi.wages + fi.comp_1042s
    schol = fi.scholarship_taxable + fi.scholarship_1042s
    total = wages + fi.interest + fi.dividends + cg + fi.se_income + schol
    adj = L.get("adj_half_se", 0.0) + L.get("adj_student_loan", 0.0)
    agi = total - adj
    diff = agi - float(L.get("agi", 0.0))
    if abs(diff) >= 1:
        parts = []
        if L.get("treaty_exempt_income"):
            parts.append(f"treaty-exempt income ${L['treaty_exempt_income']:,.0f}")
        if fed.mode == "nonresident":
            if fi.interest:
                parts.append(f"interest ${fi.interest:,.0f}")
            if fi.dividends:
                parts.append(f"dividends ${fi.dividends:,.0f}")
            if net_cg:
                parts.append(f"capital gain/loss ${cg:,.0f}")
        ex.append("California AGI differs from federal AGI by ${:,.0f}: California does not follow tax "
                  "treaties or the nonresident-alien exclusions{}.".format(
                      diff, (" (" + ", ".join(parts) + ")") if parts else ""))
    return agi, ex


def compute_california(inp: CAInput, fed: FederalResult) -> CAResult:
    R = load_rules("california")
    fs = fed.filing_status
    ex: list[str] = []
    warn: list[str] = []
    total_agi, notes = _ca_total_agi(fed, inp.fed_input)
    ex += notes

    std = R["standard_deduction"][fs]
    deduction = max(std, inp.itemized or 0.0)
    total_taxable = max(0.0, total_agi - deduction)
    tax_total = ca_tax(total_taxable, fs, R)

    # exemption credits (with AGI limitation worksheet)
    n_personal = 2 if fs == "mfj" else 1
    personal_amt = R["exemption_credit"]["personal"]
    dep_amt = R["exemption_credit"]["dependent"]
    thr = R["exemption_phaseout_agi"][fs]
    red_each = 0.0
    if total_agi > thr:
        red_each = math.ceil((total_agi - thr) / R["exemption_phaseout_step"][fs]) * R["exemption_phaseout_amount"]
        ex.append(f"Exemption credits reduced ${red_each:,.0f} each (AGI over ${thr:,}).")
    excred = n_personal * max(0.0, personal_amt - red_each) + inp.dependents * max(0.0, dep_amt - red_each)

    rc = R["renters_credit"]
    joint = fs in ("mfj", "qss", "hoh")
    limit = rc["agi_limit_mfj"] if joint else rc["agi_limit_single"]

    if inp.full_year_resident:
        tax = tax_total
        renters = (rc["mfj"] if joint else rc["single"]) if (inp.renter and total_agi <= limit) else 0.0
        credits = min(tax, excred)
        renters = min(renters, max(0.0, tax - credits))
        total_tax = max(0.0, tax - credits - renters)
        ex.append(f"Form 540: CA taxable income ${total_taxable:,.0f} (AGI ${total_agi:,.0f} − "
                  f"{'standard' if deduction == std else 'itemized'} deduction ${deduction:,.0f}); tax ${tax:,.0f}.")
        if excred:
            ex.append(f"Exemption credits ${credits:,.0f}.")
        if renters:
            ex.append(f"Nonrefundable renter's credit ${renters:,.0f}.")
        lines = {"ca_agi": total_agi, "deduction": deduction, "taxable_income": total_taxable,
                 "tax": tax, "exemption_credits": credits, "renters_credit": renters,
                 "total_tax": total_tax}
        form = "540"
    else:
        if inp.ca_source_income is not None:
            ca_agi = max(0.0, inp.ca_source_income)
        else:
            ca_agi = total_agi * max(0.0, min(1.0, inp.ca_income_ratio))
            warn.append("540NR computed from an income percentage — enter California-source income in dollars "
                        "for an exact Schedule CA (540NR).")
        ratio = 0.0 if total_agi <= 0 else max(0.0, min(1.0, ca_agi / total_agi))
        ca_ded = deduction * ratio
        ca_taxable = max(0.0, ca_agi - ca_ded)
        rate = (tax_total / total_taxable) if total_taxable else 0.0
        rate = round(rate, 4)
        tax = ca_taxable * rate
        ex_pct = min(1.0, ca_taxable / total_taxable) if total_taxable else 0.0
        ex_pct = round(ex_pct, 4)
        credits = min(tax, excred * ex_pct)
        renters = 0.0
        if inp.renter and total_agi <= limit:
            renters = min((rc["mfj"] if joint else rc["single"]) * ex_pct, max(0.0, tax - credits))
        total_tax = max(0.0, tax - credits - renters)
        ex.append(f"Form 540NR: tax on all income ${tax_total:,.0f} on ${total_taxable:,.0f} → CA tax rate "
                  f"{rate:.4f}; CA taxable income ${ca_taxable:,.0f} (CA-source AGI ${ca_agi:,.0f}, "
                  f"deduction prorated {ratio:.2%}) → CA tax ${tax:,.0f}.")
        lines = {"total_agi": total_agi, "ca_agi": ca_agi, "deduction": deduction,
                 "total_taxable_income": total_taxable, "total_tax_all_income": tax_total,
                 "ca_deduction_pct": ratio, "ca_taxable_income": ca_taxable, "ca_tax_rate": rate,
                 "tax": tax, "exemption_credit_pct": ex_pct, "exemption_credits": credits,
                 "renters_credit": renters, "total_tax": total_tax, "taxable_income": ca_taxable}
        form = "540NR"

    lines["withholding"] = inp.ca_withholding
    lines["refund"] = inp.ca_withholding - lines["total_tax"]
    out = {}
    for k, v in lines.items():
        out[k] = v if k in ("ca_deduction_pct", "ca_tax_rate", "exemption_credit_pct") else rnd(v)
    out["overpaid"] = max(0.0, out["refund"])
    out["owed"] = max(0.0, -out["refund"])
    warn.append("CalEITC / Young Child Tax Credit (FTB 3514) are not computed; low-income filers with an "
                "SSN or ITIN may qualify for a refundable credit.") if total_agi < 32000 and inp.full_year_resident else None
    return CAResult(form=form, lines=out, explanations=ex, warnings=warn)
