"""Federal tax calculation engine (TY-versioned via rules loader).

Every computed value carries an explanation so the UI can show
'how we calculated this' per the product spec.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from .rules_loader import load_rules
from .residency import ResidencyResult
from .treaty import apply_treaty


def marginal_tax(ti: float, brackets: list) -> float:
    tax = 0.0
    for i, (lo, rate) in enumerate(brackets):
        hi = brackets[i + 1][0] if i + 1 < len(brackets) else float("inf")
        if ti > lo:
            tax += (min(ti, hi) - lo) * rate
    return tax


def _phase(value: float, magi: float, rng) -> float:
    """Linear phaseout: full below lo, zero above hi."""
    if rng is None:
        return 0.0
    lo, hi = rng
    if magi <= lo:
        return value
    if magi >= hi:
        return 0.0
    return value * (hi - magi) / (hi - lo)


@dataclass
class FederalInput:
    filing_status: str = "single"
    wages: float = 0.0
    fed_withholding: float = 0.0
    interest: float = 0.0
    dividends: float = 0.0
    qualified_dividends: float = 0.0
    capital_gain_lt: float = 0.0
    capital_gain_st: float = 0.0
    se_income: float = 0.0
    scholarship_taxable: float = 0.0
    student_loan_interest: float = 0.0
    itemized: float = 0.0
    qualifying_children: int = 0
    other_dependents: int = 0
    tuition_paid: float = 0.0
    education_credit_type: str = "none"   # none|aotc|llc
    country: str = ""
    is_student: bool = False
    estimated_payments: float = 0.0


@dataclass
class FederalResult:
    year: int
    form: str
    filing_status: str
    lines: dict = field(default_factory=dict)
    explanations: list = field(default_factory=list)
    treaty: dict | None = None

    @property
    def refund(self):
        return self.lines.get("refund", 0.0)


def compute_federal(inp: FederalInput, res: ResidencyResult) -> FederalResult:
    R = load_rules("federal")
    is_nra = res.status == "nonresident"
    fs = inp.filing_status
    ex = []

    # --- NRA filing-status restriction ---
    if is_nra and fs not in R["nra"]["filing_statuses"]:
        ex.append(f"Filing status changed from {fs} to mfs: nonresident aliens generally cannot file jointly.")
        fs = "mfs"

    # --- Treaty benefits (NRA) ---
    wages = inp.wages
    scholarship = inp.scholarship_taxable
    treaty = None
    if is_nra:
        treaty = apply_treaty(inp.country, is_student=inp.is_student, wages=wages, scholarship=scholarship)
        if treaty["wage_exempt"] > 0:
            wages -= treaty["wage_exempt"]
            ex.append(f"Treaty {treaty['articles']}: ${treaty['wage_exempt']:,.0f} of wages exempt.")
        if treaty["scholarship_exempt"] > 0:
            scholarship -= treaty["scholarship_exempt"]
            ex.append(f"Treaty {treaty['articles']}: scholarship exempt.")

    # --- Income ---
    st_gain = inp.capital_gain_st
    lt_gain = inp.capital_gain_lt
    dividends = 0.0 if is_nra else inp.dividends  # NRA FDAP handled on Schedule NEC (out of ECI calc)
    se = 0.0 if is_nra else inp.se_income

    # SE tax (Schedule SE)
    se_tax = 0.0
    se_ded = 0.0
    if se > 0:
        net_earn = se * R["self_employment"]["net_earnings_factor"]
        ss_taxable = min(net_earn, max(0, R["self_employment"]["ss_wage_base"] - wages))
        se_tax = ss_taxable * R["self_employment"]["ss_rate"] + net_earn * R["self_employment"]["medicare_rate"]
        se_ded = se_tax / 2
        ex.append(f"Self-employment tax on ${net_earn:,.0f} net earnings (92.35% of ${se:,.0f}): ${se_tax:,.0f}; half deductible.")

    total_income = wages + inp.interest + dividends + st_gain + lt_gain + se + scholarship

    # --- Adjustments ---
    magi_pre = total_income - se_ded
    sl_range = R["student_loan_interest"]["magi_phaseout"].get(fs)
    sl_ded = _phase(min(inp.student_loan_interest, R["student_loan_interest"]["cap"]), magi_pre, sl_range)
    if inp.student_loan_interest > 0:
        ex.append(f"Student loan interest deduction: ${sl_ded:,.0f} (capped at ${R['student_loan_interest']['cap']:,}, MAGI phaseout applied).")

    agi = max(0.0, total_income - se_ded - sl_ded)

    # --- Deduction ---
    std = R["standard_deduction"].get(fs, R["standard_deduction"]["single"])
    if is_nra:
        if treaty and treaty.get("standard_deduction"):
            ex.append(f"Standard deduction ${std:,.0f} allowed under treaty {treaty['articles']} (India student rule).")
            deduction = max(std, inp.itemized)
        else:
            deduction = inp.itemized
            ex.append("Nonresident aliens cannot claim the standard deduction; itemized deductions (e.g., state tax withheld) applied.")
    else:
        deduction = max(std, inp.itemized)
        ex.append(f"{'Itemized' if inp.itemized > std else 'Standard'} deduction ${deduction:,.0f} applied.")

    taxable = max(0.0, agi - deduction)

    # --- Tax: split ordinary vs preferential (LTCG + qualified dividends) ---
    pref = max(0.0, lt_gain) + (0.0 if is_nra else inp.qualified_dividends)
    pref = min(pref, taxable)
    ordinary_ti = taxable - pref
    tax_ordinary = marginal_tax(ordinary_ti, R["brackets"][fs])
    tax_pref = 0.0
    if pref > 0:
        # stack preferential income on top of ordinary income
        lt = R["ltcg_brackets"][fs]
        for i, (lo, rate) in enumerate(lt):
            hi = lt[i + 1][0] if i + 1 < len(lt) else float("inf")
            seg_lo = max(lo, ordinary_ti)
            seg_hi = min(hi, taxable)
            if seg_hi > seg_lo:
                tax_pref += (seg_hi - seg_lo) * rate
        ex.append(f"Long-term gains/qualified dividends ${pref:,.0f} taxed at preferential rates: ${tax_pref:,.0f}.")
    tax = tax_ordinary + tax_pref

    # --- Nonrefundable credits ---
    ctc_cfg = R["child_tax_credit"]
    ctc = actc = odc = 0.0
    if not is_nra and (inp.qualifying_children or inp.other_dependents):
        gross_ctc = inp.qualifying_children * ctc_cfg["per_child"]
        odc = inp.other_dependents * ctc_cfg["other_dependent_credit"]
        po = ctc_cfg["phaseout_agi"][fs]
        if agi > po:
            reduction = -(-int(agi - po) // 1000) * ctc_cfg["phaseout_rate_per_1000"]
            gross_ctc = max(0.0, gross_ctc + odc - reduction) - odc if gross_ctc + odc > reduction else 0.0
            odc = min(odc, max(0.0, gross_ctc + odc))
            ex.append(f"CTC/ODC reduced by ${reduction:,.0f} — AGI over ${po:,}.")
        ctc = min(gross_ctc, max(0.0, tax - 0))
        # refundable ACTC
        unused = gross_ctc - ctc
        if unused > 0:
            earned = wages + se
            actc = min(unused,
                       inp.qualifying_children * ctc_cfg["refundable_max_per_child"],
                       max(0.0, (earned - ctc_cfg["earned_income_floor"])) * ctc_cfg["refundable_rate"])
            if actc:
                ex.append(f"Additional (refundable) child tax credit: ${actc:,.0f}.")

    edu_credit = edu_refundable = 0.0
    if not is_nra and inp.education_credit_type != "none" and inp.tuition_paid > 0:
        ec = R["education_credits"]
        rng = ec["magi_phaseout"].get(fs)
        if inp.education_credit_type == "aotc":
            base = min(inp.tuition_paid, ec["aotc"]["max_expense_100pct"]) + \
                   ec["aotc"]["rate_2nd_tier"] * max(0.0, min(inp.tuition_paid - 2000, ec["aotc"]["max_expense_2nd_tier"]))
            base = _phase(base, agi, rng)
            edu_refundable = base * ec["aotc"]["refundable_share"]
            edu_credit = min(base - edu_refundable, max(0.0, tax - ctc - odc))
            ex.append(f"American Opportunity Credit ${base:,.0f} (${edu_refundable:,.0f} refundable).")
        else:
            base = _phase(ec["llc"]["rate"] * min(inp.tuition_paid, ec["llc"]["expense_cap"]), agi, rng)
            edu_credit = min(base, max(0.0, tax - ctc - odc))
            ex.append(f"Lifetime Learning Credit ${edu_credit:,.0f}.")

    # --- EITC ---
    eitc = 0.0
    if not is_nra:
        kids = min(inp.qualifying_children, 3)
        p = R["eitc"]["by_children"][kids]
        rate_in, ei_amt, max_credit, rate_out, po_s, po_mfj = p
        inv = inp.interest + inp.dividends + lt_gain + st_gain
        earned = wages + se
        if 0 < earned and inv <= R["eitc"]["investment_income_limit"] and fs != "mfs":
            credit = min(earned * rate_in, max_credit)
            po_start = po_mfj if fs in ("mfj", "qss") else po_s
            over = max(agi, earned) - po_start
            if over > 0:
                credit = max(0.0, credit - over * rate_out)
            eitc = credit
            if eitc:
                ex.append(f"Earned Income Credit: ${eitc:,.0f}.")

    # --- Other taxes ---
    addl_medicare = 0.0
    thr = R["additional_medicare"]["threshold"][fs]
    medicare_wages = wages + (se * R["self_employment"]["net_earnings_factor"] if se else 0)
    if medicare_wages > thr:
        addl_medicare = (medicare_wages - thr) * R["additional_medicare"]["rate"]
        ex.append(f"Additional Medicare Tax (Form 8959): ${addl_medicare:,.0f}.")

    niit = 0.0
    if not is_nra:
        nt = R["niit"]["magi_threshold"][fs]
        net_inv = inp.interest + inp.dividends + lt_gain + st_gain
        if agi > nt and net_inv > 0:
            niit = R["niit"]["rate"] * min(net_inv, agi - nt)
            ex.append(f"Net Investment Income Tax (Form 8960): ${niit:,.0f}.")

    total_tax = max(0.0, tax - ctc - odc - edu_credit) + se_tax + addl_medicare + niit
    payments = inp.fed_withholding + inp.estimated_payments + actc + edu_refundable + eitc
    refund = payments - total_tax

    r = lambda v: round(v)
    lines = {
        "1a_wages": r(wages), "2b_interest": r(inp.interest), "3b_dividends": r(dividends),
        "7_capital_gain": r(st_gain + lt_gain), "8_other_income": r(scholarship + se),
        "9_total_income": r(total_income), "10_adjustments": r(se_ded + sl_ded),
        "11_agi": r(agi), "12_deduction": r(deduction), "15_taxable_income": r(taxable),
        "16_tax": r(tax), "19_ctc_odc": r(ctc + odc), "20_other_credits": r(edu_credit),
        "22_after_credits": r(max(0.0, tax - ctc - odc - edu_credit)),
        "23_other_taxes": r(se_tax + addl_medicare + niit),
        "24_total_tax": r(total_tax), "25_withholding": r(inp.fed_withholding),
        "27_eitc": r(eitc), "28_actc": r(actc), "29_aotc_refundable": r(edu_refundable),
        "33_total_payments": r(payments),
        "refund": r(refund),
    }
    return FederalResult(year=R["year"], form=res.form, filing_status=fs,
                         lines=lines, explanations=ex, treaty=treaty)
