"""Federal tax calculation engine, TY-versioned via the rules loader.

Three computation modes, chosen from the residency result:
  resident     (citizen / resident alien)  -> Form 1040
  nonresident                              -> Form 1040-NR (+ Schedule OI, Schedule NEC)
  dual_status                              -> Form 1040 "Dual-Status Return" + 1040-NR statement

The engine returns *semantic* line values (see LINE_KEYS) plus a plain-language explanation for
each step.  The PDF layer maps semantic keys onto the official form fields.
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from .rules_loader import load_rules
from .residency import ResidencyResult
from .treaty import apply_treaty, fdap_dividend_rate


# --------------------------------------------------------------------------------------------
# tax computation helpers
# --------------------------------------------------------------------------------------------
def marginal_tax(ti: float, brackets: list) -> float:
    tax = 0.0
    for i, (lo, rate) in enumerate(brackets):
        hi = brackets[i + 1][0] if i + 1 < len(brackets) else float("inf")
        if ti > lo:
            tax += (min(ti, hi) - lo) * rate
    return tax


def rnd(x: float) -> float:
    """Round half up to whole dollars (IRS convention; Python's round() is banker's rounding)."""
    return float(math.floor(x + 0.5 + 1e-9))


def table_midpoint(amount: float) -> float:
    """IRS Tax Table / EIC Table convention: income under $100,000 is looked up by band and the
    tax is the rate-schedule tax on the band midpoint ($5/$10 bands below $25, $25 bands below
    $3,000, $50 bands from $3,000)."""
    if amount < 5:
        return 0.0
    if amount < 15:
        return 10.0
    if amount < 25:
        return 20.0
    width = 25 if amount < 3000 else 50
    lo = math.floor(amount / width) * width
    return lo + width / 2


def regular_tax(ti: float, fs: str, R: dict) -> float:
    """Tax on ordinary taxable income exactly as Form 1040 line 16 requires (Tax Table < $100k)."""
    if ti <= 0:
        return 0.0
    br = R["brackets"][fs]
    if ti < 100000:
        return rnd(marginal_tax(table_midpoint(ti), br))
    return marginal_tax(ti, br)


def tax_with_preferential(ti: float, pref: float, fs: str, R: dict) -> tuple[float, float]:
    """Qualified Dividends and Capital Gain Tax Worksheet. Returns (total tax, tax on pref part)."""
    pref = max(0.0, min(pref, ti))
    if pref <= 0:
        return regular_tax(ti, fs, R), 0.0
    ordinary = ti - pref
    lt = R["ltcg_brackets"][fs]
    tax_pref = 0.0
    for i, (lo, rate) in enumerate(lt):
        hi = lt[i + 1][0] if i + 1 < len(lt) else float("inf")
        seg_lo, seg_hi = max(lo, ordinary), min(hi, ti)
        if seg_hi > seg_lo:
            tax_pref += (seg_hi - seg_lo) * rate
    total = regular_tax(ordinary, fs, R) + tax_pref
    return min(total, regular_tax(ti, fs, R)), tax_pref     # worksheet line 24/25: never more


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


# --------------------------------------------------------------------------------------------
# inputs / outputs
# --------------------------------------------------------------------------------------------
@dataclass
class FederalInput:
    filing_status: str = "single"
    # W-2 (sums across all W-2s)
    wages: float = 0.0                    # box 1
    medicare_wages: float | None = None   # box 5 (defaults to box 1)
    fed_withholding: float = 0.0          # box 2 (+ 1099 box 4 withholding)
    wages_nr_period: float = 0.0          # dual-status: part of box 1 earned before residency start
    # Form 1042-S
    comp_1042s: float = 0.0               # treaty-exempt compensation reported on 1042-S (codes 17-20)
    scholarship_1042s: float = 0.0        # gross scholarship/fellowship on 1042-S (code 16)
    withholding_1042s: float = 0.0        # 1042-S box 7a (or 10)
    # investment
    interest: float = 0.0
    dividends: float = 0.0                # ordinary (1099-DIV box 1a)
    qualified_dividends: float = 0.0      # 1099-DIV box 1b
    capital_gain_lt: float = 0.0
    capital_gain_st: float = 0.0
    # other income
    se_income: float = 0.0                # net profit (1099-NEC minus business expenses)
    scholarship_taxable: float = 0.0      # taxable scholarship not on W-2 (grants minus tuition/books)
    # adjustments / deductions
    student_loan_interest: float = 0.0
    itemized: float = 0.0                 # legacy: total itemized deductions already computed
    state_income_tax_paid: float = 0.0    # Schedule A line 5a (state withholding + payments)
    charitable: float = 0.0
    other_itemized: float = 0.0           # mortgage interest etc. (residents)
    qualified_tips: float = 0.0           # Schedule 1-A
    qualified_overtime: float = 0.0       # Schedule 1-A (FLSA premium portion only)
    has_ssn: bool = True
    age: int = 0                          # 0 = unknown
    # dependents & education
    qualifying_children: int = 0
    other_dependents: int = 0
    tuition_paid: float = 0.0
    education_credit_type: str = "none"   # none|aotc|llc
    # treaty / presence
    country: str = ""
    is_student: bool = False
    days_present: int = 0                 # physical presence in tax year (NRA capital-gain 183-day rule)
    first_entry_year: int = 0
    estimated_payments: float = 0.0


@dataclass
class FederalResult:
    year: int
    form: str
    filing_status: str
    mode: str = "resident"
    lines: dict = field(default_factory=dict)
    explanations: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    treaty: dict | None = None
    schedules: list = field(default_factory=list)

    @property
    def refund(self):
        return self.lines.get("refund", 0.0)


NRA_FS = {"single": "single", "mfs": "mfs", "qss": "qss", "mfj": "mfs", "hoh": "single"}
DUAL_FS = {"single": "single", "mfs": "mfs", "mfj": "mfs", "hoh": "single", "qss": "single"}


def compute_federal(inp: FederalInput, res: ResidencyResult) -> FederalResult:
    R = load_rules("federal")
    mode = {"nonresident": "nonresident", "dual_status": "dual_status"}.get(res.status, "resident")
    ex: list[str] = []
    warn: list[str] = list(getattr(res, "warnings", []) or [])
    sched: list[str] = []

    fs = inp.filing_status if inp.filing_status in R["standard_deduction"] else "single"
    if mode == "nonresident" and NRA_FS[fs] != fs:
        ex.append(f"Filing status changed from {fs.upper()} to {NRA_FS[fs].upper()}: nonresident aliens "
                  f"cannot file jointly or as head of household.")
        fs = NRA_FS[fs]
    if mode == "dual_status" and DUAL_FS[fs] != fs:
        ex.append(f"Filing status changed from {fs.upper()} to {DUAL_FS[fs].upper()}: dual-status filers cannot "
                  f"file jointly, as head of household or as qualifying surviving spouse (unless they elect "
                  f"full-year residency with a U.S. citizen/resident spouse).")
        fs = DUAL_FS[fs]

    # ---------------- treaty ---------------------------------------------------------------
    years_in_us = (R["year"] - inp.first_entry_year + 1) if inp.first_entry_year else 0
    treaty = None
    treaty_wages_base = 0.0
    if mode == "nonresident":
        treaty_wages_base = inp.wages + inp.comp_1042s
    elif mode == "dual_status":
        treaty_wages_base = min(inp.wages_nr_period, inp.wages) + inp.comp_1042s
    elif res.status == "resident" and inp.country:   # resident alien: saving-clause exceptions only
        treaty_wages_base = inp.wages + inp.comp_1042s
    if inp.country and (mode != "resident" or res.status == "resident"):
        treaty = apply_treaty(inp.country, is_student=inp.is_student, wages=treaty_wages_base,
                              scholarship=inp.scholarship_1042s + inp.scholarship_taxable,
                              resident_alien=(mode == "resident"), years_in_us=years_in_us)
        warn += treaty.get("warnings", [])
    exempt_wages = treaty["wage_exempt"] if treaty else 0.0
    exempt_schol = treaty["scholarship_exempt"] if treaty else 0.0
    # Treaty-exempt pay already left out of W-2 box 1 (reported on 1042-S) must not be subtracted again.
    exempt_in_w2 = max(0.0, exempt_wages - inp.comp_1042s)
    wages = max(0.0, inp.wages - exempt_in_w2)
    if exempt_wages:
        ex.append(f"Tax treaty ({inp.country}, {treaty['articles']}): ${exempt_wages:,.0f} of wages is exempt from "
                  f"U.S. tax" + (" (reported on line 1k / Schedule OI item L)." if mode == "nonresident" else "."))
    scholarship_gross = inp.scholarship_taxable + inp.scholarship_1042s
    scholarship = max(0.0, scholarship_gross - exempt_schol)
    if exempt_schol:
        ex.append(f"Tax treaty ({inp.country}): ${exempt_schol:,.0f} of scholarship/fellowship income is exempt.")

    is_nra = mode == "nonresident"

    # ---------------- investment income ----------------------------------------------------
    cl_limit = R["capital_loss_limit"][fs]
    nec_tax = nec_div = nec_cg = 0.0
    nec_div_rate = 0.0
    interest = inp.interest
    dividends, qdiv = inp.dividends, min(inp.qualified_dividends, inp.dividends)
    st, lt = inp.capital_gain_st, inp.capital_gain_lt
    if is_nra:
        if interest:
            ex.append(f"Bank/portfolio interest of ${interest:,.0f} is not taxable to a nonresident alien "
                      f"(IRC 871(i)/871(h)) and is left off Form 1040-NR.")
        interest = 0.0
        if dividends:
            nec_div_rate = fdap_dividend_rate(inp.country, R["nra"]["fdap_default_rate"])
            nec_div = dividends
            ex.append(f"U.S. dividends ${dividends:,.0f} are not effectively connected income: taxed at a flat "
                      f"{nec_div_rate:.0%} on Schedule NEC" + (" (treaty rate)." if nec_div_rate < 0.30 else "."))
        dividends = qdiv = 0.0
        net_cg = st + lt
        if net_cg > 0 and inp.days_present >= R["nra"]["capital_gains_days_threshold"]:
            nec_cg = net_cg
            ex.append(f"Net capital gain ${net_cg:,.0f}: you were in the U.S. {inp.days_present} days (183+), so "
                      f"U.S.-source capital gains are taxed at 30% on Schedule NEC (losses are not deductible "
                      f"against other income).")
        elif net_cg:
            ex.append("Capital gains/losses are not taxable to a nonresident alien present fewer than 183 days "
                      "and are left off the return.")
        st = lt = 0.0
        nec_tax = nec_div * nec_div_rate + nec_cg * R["nra"]["capital_gains_rate"]
        if nec_tax:
            sched.append("Schedule NEC (Form 1040-NR)")

    net_cg = st + lt
    cap_line = net_cg if net_cg >= 0 else max(net_cg, -cl_limit)
    if net_cg < -cl_limit:
        ex.append(f"Net capital loss ${-net_cg:,.0f} limited to ${cl_limit:,.0f} this year; "
                  f"${-net_cg - cl_limit:,.0f} carries forward.")
    pref_gain = max(0.0, min(lt, net_cg))         # net capital gain eligible for 0/15/20% rates
    if st or lt:
        sched += ["Schedule D", "Form 8949"]

    # ---------------- self-employment ------------------------------------------------------
    se = inp.se_income
    se_tax = se_ded = 0.0
    if se and not is_nra:
        net_earn = se * R["self_employment"]["net_earnings_factor"]
        if net_earn >= R["se_minimum_net_earnings"]:
            ss_base = max(0.0, R["self_employment"]["ss_wage_base"] - inp.wages)
            se_tax = min(net_earn, ss_base) * R["self_employment"]["ss_rate"] + \
                net_earn * R["self_employment"]["medicare_rate"]
            se_ded = se_tax / 2
            sched.append("Schedule SE")
            ex.append(f"Self-employment tax on ${net_earn:,.0f} (92.35% of ${se:,.0f} net profit): "
                      f"${se_tax:,.0f}; half (${se_ded:,.0f}) is deductible.")
    elif se and is_nra:
        ex.append(f"Self-employment profit ${se:,.0f} is taxed as effectively connected income. Nonresident "
                  f"aliens do not owe self-employment (Social Security/Medicare) tax.")
    if se:
        sched.append("Schedule C")

    # ---------------- total income / AGI ---------------------------------------------------
    other_income = se + scholarship                     # Schedule 1 lines 3 + 8r
    total_income = wages + interest + dividends + cap_line + other_income
    if other_income or se_ded or inp.student_loan_interest:
        sched.append("Schedule 1")
    magi_pre = total_income - se_ded
    sl_rng = R["student_loan_interest"]["magi_phaseout"].get(fs)
    sl_ded = _phase(min(inp.student_loan_interest, R["student_loan_interest"]["cap"]), magi_pre, sl_rng)
    if inp.student_loan_interest:
        if fs == "mfs":
            ex.append("Student loan interest is not deductible when married filing separately.")
        else:
            ex.append(f"Student loan interest deduction ${sl_ded:,.0f} (max $2,500, reduced by income).")
    adjustments = se_ded + sl_ded
    agi = total_income - adjustments

    # ---------------- deductions -----------------------------------------------------------
    std = R["standard_deduction"][fs]
    salt_cfg = R["salt_cap"]
    salt_cap = salt_cfg["cap"][fs]
    over = max(0.0, agi - salt_cfg["phase_down_magi"][fs])
    salt_cap = max(salt_cfg["floor"][fs], salt_cap - over * salt_cfg["phase_down_rate"])
    salt = min(inp.state_income_tax_paid, salt_cap)
    if is_nra or mode == "dual_status":
        item = salt + inp.charitable + (inp.other_itemized if mode == "dual_status" else 0.0)
    else:
        item = salt + inp.charitable + inp.other_itemized
    item = max(item, inp.itemized)
    if (item or inp.state_income_tax_paid) and inp.state_income_tax_paid > salt_cap:
        ex.append(f"State and local tax deduction capped at ${salt_cap:,.0f}.")

    if mode == "resident":
        deduction = max(std, item)
        ded_type = "itemized" if item > std else "standard"
        ex.append(f"{ded_type.title()} deduction ${deduction:,.0f}.")
    elif is_nra and treaty and treaty.get("standard_deduction"):
        deduction = max(std, item)
        ded_type = "itemized" if item > std else "standard"
        ex.append(f"India treaty Art. 21(2): students may take the standard deduction (${std:,.0f}) on Form "
                  f"1040-NR; the larger of standard or itemized is used (${deduction:,.0f}).")
    else:
        deduction, ded_type = item, "itemized"
        who = "Nonresident aliens" if is_nra else "Dual-status filers"
        ex.append(f"{who} cannot take the standard deduction; itemized deductions "
                  f"(state income tax withheld, U.S. charitable gifts) of ${deduction:,.0f} applied.")
    if ded_type == "itemized" and deduction > 0:
        sched.append("Schedule A (Form 1040-NR)" if is_nra else "Schedule A")

    # ---------------- Schedule 1-A (tips / overtime) --------------------------------------
    s1a = R["schedule_1a"]
    tips_ded = ot_ded = 0.0
    if (inp.qualified_tips or inp.qualified_overtime):
        if fs == "mfs":
            ex.append("Tips/overtime deductions are not allowed when married filing separately.")
        elif not inp.has_ssn:
            ex.append("Tips/overtime deductions require a Social Security number valid for employment.")
        else:
            jt = fs == "mfj"
            red = max(0, math.ceil(max(0.0, agi - s1a["phaseout_magi"][fs]) / 1000)) * s1a["phaseout_per_1000"]
            tips_ded = max(0.0, min(inp.qualified_tips, s1a["tips"]["cap_mfj" if jt else "cap"]) - red)
            ot_ded = max(0.0, min(inp.qualified_overtime, s1a["overtime"]["cap_mfj" if jt else "cap"]) - red)
            if tips_ded or ot_ded:
                sched.append("Schedule 1-A")
                ex.append(f"Schedule 1-A: qualified tips ${tips_ded:,.0f}, qualified overtime ${ot_ded:,.0f} deducted.")
    s1a_total = tips_ded + ot_ded

    taxable = max(0.0, agi - deduction - s1a_total)

    # ---------------- tax ------------------------------------------------------------------
    pref = pref_gain + qdiv
    tax, tax_pref = tax_with_preferential(taxable, pref, fs, R)
    if tax_pref or (pref and taxable):
        ex.append(f"Long-term gains/qualified dividends (${min(pref, taxable):,.0f}) taxed at 0/15/20% rates.")
    ex.append(f"Tax on ${taxable:,.0f} taxable income: ${tax:,.0f}"
              + (" (IRS Tax Table)." if taxable < 100000 else " (Tax Computation Worksheet)."))

    # ---------------- credits --------------------------------------------------------------
    edu_nonref = edu_ref = 0.0
    if inp.education_credit_type != "none" and inp.tuition_paid > 0:
        if mode != "resident":
            ex.append("Education credits are not available to nonresident or dual-status aliens "
                      "(unless married and electing to be treated as a resident).")
        elif fs == "mfs":
            ex.append("Education credits are not allowed when married filing separately.")
        else:
            ec = R["education_credits"]
            rng = ec["magi_phaseout"].get(fs)
            if inp.education_credit_type == "aotc":
                base = min(inp.tuition_paid, ec["aotc"]["max_expense_100pct"]) + ec["aotc"]["rate_2nd_tier"] * \
                    max(0.0, min(inp.tuition_paid - ec["aotc"]["max_expense_100pct"], ec["aotc"]["max_expense_2nd_tier"]))
                base = _phase(base, agi, rng)
                edu_ref = rnd(base * ec["aotc"]["refundable_share"])
                edu_nonref = min(base - edu_ref, tax)
                ex.append(f"American Opportunity Credit ${base:,.0f}: ${edu_ref:,.0f} refundable, "
                          f"${edu_nonref:,.0f} applied against tax.")
            else:
                base = _phase(ec["llc"]["rate"] * min(inp.tuition_paid, ec["llc"]["expense_cap"]), agi, rng)
                edu_nonref = min(base, tax)
                ex.append(f"Lifetime Learning Credit ${edu_nonref:,.0f}.")
            sched += ["Form 8863", "Schedule 3"]

    ctc = actc = odc = 0.0
    kids, deps = inp.qualifying_children, inp.other_dependents
    if (kids or deps) and is_nra:
        ex.append("Child tax credit is generally not available on Form 1040-NR (exceptions exist for residents "
                  "of Canada, Mexico, South Korea and Indian students — not computed here).")
    elif kids or deps:
        cfg = R["child_tax_credit"]
        gross = kids * cfg["per_child"] + deps * cfg["other_dependent_credit"]
        po = cfg["phaseout_agi"][fs]
        if agi > po:
            reduction = math.ceil((agi - po) / 1000) * cfg["phaseout_rate_per_1000"]
            gross = max(0.0, gross - reduction)
            ex.append(f"Child/dependent credits reduced by ${reduction:,.0f} (AGI over ${po:,}).")
        limit = max(0.0, tax - edu_nonref)
        allowed = min(gross, limit)
        child_part = min(gross, kids * cfg["per_child"])
        odc_part = gross - child_part
        odc = min(odc_part, allowed)                 # ODC uses the limit first (nonrefundable only)
        ctc = allowed - odc
        unused_ctc = max(0.0, child_part - ctc)
        if unused_ctc > 0 and kids:
            earned = wages + max(0.0, se - se_ded)
            actc = min(unused_ctc, kids * cfg["refundable_max_per_child"],
                       max(0.0, earned - cfg["earned_income_floor"]) * cfg["refundable_rate"])
            actc = rnd(actc)
        sched.append("Schedule 8812")
        ex.append(f"Child tax credit / credit for other dependents ${ctc + odc:,.0f}"
                  + (f"; additional (refundable) child tax credit ${actc:,.0f}." if actc else "."))

    # ---------------- EITC (full-year residents only) --------------------------------------
    eitc = 0.0
    if mode == "resident":
        k = min(kids, 3)
        rate_in, ei_amt, max_credit, rate_out, po_s, po_mfj = R["eitc"]["by_children"][k]
        inv = inp.interest + inp.dividends + max(0.0, net_cg)
        earned = wages + (se - se_ded if se else 0.0)
        lo_age, hi_age = R["eitc_age_no_children"]
        age_ok = k > 0 or inp.age == 0 or lo_age <= inp.age <= hi_age
        if k == 0 and inp.age and not age_ok:
            ex.append(f"No Earned Income Credit: without a qualifying child you must be age {lo_age}-{hi_age}.")
        elif earned > 0 and inv <= R["eitc"]["investment_income_limit"] and fs != "mfs" and inp.has_ssn:
            po_start = po_mfj if fs == "mfj" else po_s

            def credit_for(x):
                x = table_midpoint(x) if x < 100000 else x
                c = min(x * rate_in, max_credit)
                return max(0.0, c - max(0.0, x - po_start) * rate_out)
            eitc = credit_for(earned)
            if agi >= po_start:
                eitc = min(eitc, credit_for(agi))
            eitc = rnd(eitc)
            if eitc:
                ex.append(f"Earned Income Credit ${eitc:,.0f}.")
                if k == 0 and not inp.age:
                    warn.append("EIC without children requires age 25-64 at year end — confirm your age.")

    # ---------------- other taxes ----------------------------------------------------------
    am = R["additional_medicare"]
    med_wages = inp.medicare_wages if inp.medicare_wages is not None else inp.wages
    med_se = se * R["self_employment"]["net_earnings_factor"] if se_tax else 0.0
    addl_med = 0.0
    thr = am["threshold"][fs]
    if med_wages + med_se > thr:
        addl_med = (max(0.0, med_wages - thr) + max(0.0, med_se - max(0.0, thr - med_wages))) * am["rate"]
        sched += ["Form 8959", "Schedule 2"]
        ex.append(f"Additional Medicare Tax (Form 8959): ${addl_med:,.0f}.")
    niit = 0.0
    if mode == "resident":
        nt = R["niit"]["magi_threshold"][fs]
        net_inv = inp.interest + inp.dividends + max(0.0, net_cg)
        if agi > nt and net_inv > 0:
            niit = R["niit"]["rate"] * min(net_inv, agi - nt)
            sched += ["Form 8960", "Schedule 2"]
            ex.append(f"Net Investment Income Tax (Form 8960): ${niit:,.0f}.")
    if se_tax:
        sched.append("Schedule 2")

    total_credits = ctc + odc + edu_nonref
    tax_after = max(0.0, tax - total_credits)
    other_taxes = se_tax + addl_med + niit
    total_tax = tax_after + other_taxes + nec_tax
    wh_total = inp.fed_withholding + inp.withholding_1042s
    payments = wh_total + inp.estimated_payments + eitc + actc + edu_ref
    refund = payments - total_tax

    r = rnd
    lines = {
        "wages": r(wages), "treaty_exempt_income": r(exempt_wages + exempt_schol),
        "total_wages": r(wages), "taxable_interest": r(interest),
        "qualified_dividends": r(qdiv), "ordinary_dividends": r(dividends),
        "capital_gain": r(cap_line), "sched1_business": r(se if not math.isclose(se, 0) else 0),
        "sched1_scholarship": r(scholarship), "other_income": r(other_income),
        "total_income": r(total_income), "adj_half_se": r(se_ded), "adj_student_loan": r(sl_ded),
        "adjustments": r(adjustments), "agi": r(agi), "deduction": r(deduction),
        "deduction_type": ded_type, "salt_deduction": r(salt), "charitable": r(inp.charitable),
        "sched1a_tips": r(tips_ded), "sched1a_overtime": r(ot_ded), "sched1a_total": r(s1a_total),
        "total_deductions": r(deduction + s1a_total), "taxable_income": r(taxable), "tax": r(tax),
        "ctc_odc": r(ctc + odc), "education_credit": r(edu_nonref), "other_credits": r(edu_nonref),
        "total_credits": r(total_credits), "tax_after_credits": r(tax_after),
        "se_tax": r(se_tax), "addl_medicare": r(addl_med), "niit": r(niit),
        "other_taxes": r(other_taxes), "nec_tax": r(nec_tax), "nec_dividends": r(nec_div),
        "nec_dividend_rate": nec_div_rate, "nec_capital_gains": r(nec_cg),
        "total_tax": r(total_tax), "withholding_w2": r(inp.fed_withholding),
        "withholding_1042s": r(inp.withholding_1042s), "withholding_total": r(wh_total),
        "estimated_payments": r(inp.estimated_payments), "eitc": r(eitc), "actc": r(actc),
        "aotc_refundable": r(edu_ref), "total_payments": r(payments),
        "refund": r(refund),
    }
    lines["overpaid"] = max(0.0, lines["refund"])
    lines["owed"] = max(0.0, -lines["refund"])
    form = {"nonresident": "1040-NR", "dual_status": "1040 (Dual-Status)"}.get(mode, "1040")
    if mode == "dual_status":
        sched.append("Form 1040-NR (dual-status statement)")
        warn.append("Dual-status return: income other than wages is assumed received while a resident. "
                    "Write 'Dual-Status Return' across the top of Form 1040 and attach the 1040-NR statement; "
                    "dual-status returns must be filed on paper.")
    if treaty and treaty.get("articles") and (exempt_wages or exempt_schol or treaty.get("standard_deduction")):
        if is_nra or mode == "dual_status":
            sched.append("Schedule OI (Form 1040-NR)")
        if treaty.get("form_8833_required"):
            sched.append("Form 8833")
    return FederalResult(year=R["year"], form=form, filing_status=fs, mode=mode, lines=lines,
                         explanations=ex, warnings=warn, treaty=treaty,
                         schedules=list(dict.fromkeys(sched)))
