"""Engine tests — expected values hand-computed from TY2025 law (IRS Tax Table midpoint method,
FTB/NY 2025 rate schedules). See BUILD_LOG.txt for the arithmetic."""
import pytest
from app.engines.residency import determine_residency
from app.engines.federal import compute_federal, FederalInput, marginal_tax, regular_tax, table_midpoint
from app.engines.california import compute_california, CAInput
from app.engines.rules_loader import load_rules
from app.engines.interview import next_questions, progress, evaluate
from app.engines.treaty import apply_treaty

R = load_rules("federal")


# ---------- residency ----------
def test_citizen():
    r = determine_residency(citizen=True, green_card=False)
    assert r.status == "citizen" and r.form == "1040"

def test_green_card():
    assert determine_residency(citizen=False, green_card=True).status == "resident"

def test_f1_exempt_year3_all_prior_days_excluded():
    r = determine_residency(citizen=False, green_card=False, visa="F-1", first_entry_year=2023,
                            days_current=365, days_prior1=365, days_prior2=120)
    assert r.status == "nonresident" and r.form_8843_required and r.weighted_days == 0

def test_f1_year6_counts_only_nonexempt_days():
    # first year 2020: 2020-2024 exempt; 2025 (year 6) days count; 2024/2023 days were exempt
    r = determine_residency(citizen=False, green_card=False, visa="F-1", first_entry_year=2020,
                            days_current=365, days_prior1=365, days_prior2=365)
    assert r.status == "resident" and r.weighted_days == 365 and not r.form_8843_required

def test_f1_to_h1b_oct1_in_exempt_year_is_nonresident():
    # Most common student case: F-1 since 2021, H-1B from Oct 1 2025 -> only 92 days count
    r = determine_residency(citizen=False, green_card=False, visa="H-1B", first_entry_year=2021,
                            days_current=365, days_prior1=365, days_prior2=365,
                            exempt_days_current=273, exempt_days_prior1=365, exempt_days_prior2=365)
    assert r.status == "nonresident" and r.weighted_days == 92 and r.form_8843_required

def test_h1b_spt_not_met():
    r = determine_residency(citizen=False, green_card=False, visa="H-1B", first_entry_year=2025, days_current=100)
    assert r.status == "nonresident"

def test_h1b_arrival_midyear_is_dual_status():
    r = determine_residency(citizen=False, green_card=False, visa="H-1B", first_entry_year=2025,
                            days_current=200, first_nonexempt_day="2025-06-15")
    assert r.status == "dual_status" and r.residency_start == "2025-06-15"

def test_j1_researcher_two_year_rule():
    r = determine_residency(citizen=False, green_card=False, visa="J-1 Non-student", first_entry_year=2024,
                            days_current=365, days_prior1=365)
    assert r.status == "nonresident"           # 2024, 2025 exempt
    r = determine_residency(citizen=False, green_card=False, visa="J-1 Non-student", first_entry_year=2023,
                            days_current=365, days_prior1=365, days_prior2=365)
    assert r.status == "resident"              # exempt 2023-2024 -> 2025 days count (365)


# ---------- tax table ----------
def test_tax_table_midpoint():
    assert table_midpoint(44250) == 44275 and table_midpoint(44299.99) == 44275
    assert table_midpoint(2010) == 2012.5 and table_midpoint(10) == 10
    assert regular_tax(44250, "single", R) == 5075      # IRS 2025 Tax Table, single 44,250-44,300
    assert regular_tax(29250, "single", R) == 3275      # half-up rounding (3274.50)

def test_rate_schedule_over_100k():
    assert regular_tax(150000, "single", R) == pytest.approx(marginal_tax(150000, R["brackets"]["single"]))


# ---------- federal: residents ----------
RES = determine_residency(citizen=True, green_card=False)

def test_single_w2_only():
    f = compute_federal(FederalInput(wages=60000, fed_withholding=6000), RES)
    L = f.lines
    assert (L["agi"], L["deduction"], L["taxable_income"], L["tax"]) == (60000, 15750, 44250, 5075)
    assert L["refund"] == 925

def test_ctc_two_kids():
    f = compute_federal(FederalInput(filing_status="mfj", wages=120000, qualifying_children=2), RES)
    assert f.lines["ctc_odc"] == 4400

def test_actc_and_eitc_low_income_hoh():
    f = compute_federal(FederalInput(filing_status="hoh", wages=25000, qualifying_children=2), RES)
    assert f.lines["tax"] == 139 and f.lines["ctc_odc"] == 139
    assert f.lines["actc"] == 3375            # 15% x (25,000 - 2,500)
    assert f.lines["eitc"] == 6799            # EIC table 25,000-25,050, 2 children

def test_eitc_no_children_age_limit():
    f = compute_federal(FederalInput(wages=9000, age=22), RES)
    assert f.lines["eitc"] == 0
    f = compute_federal(FederalInput(wages=9000, age=30), RES)
    assert f.lines["eitc"] > 0

def test_odc_does_not_exceed_tax():
    f = compute_federal(FederalInput(filing_status="hoh", wages=24000, other_dependents=1), RES)
    assert f.lines["ctc_odc"] <= f.lines["tax"]

def test_student_loan_phaseout_gone():
    f = compute_federal(FederalInput(wages=120000, student_loan_interest=2500), RES)
    assert f.lines["adjustments"] == 0

def test_se_tax():
    f = compute_federal(FederalInput(se_income=50000), RES)
    net = 50000 * 0.9235
    assert f.lines["se_tax"] == round(net * 0.153)

def test_se_tax_under_400_net_earnings():
    assert compute_federal(FederalInput(se_income=400), RES).lines["se_tax"] == 0

def test_capital_loss_limited_to_3000():
    f = compute_federal(FederalInput(wages=50000, capital_gain_st=-10000), RES)
    assert f.lines["capital_gain"] == -3000 and f.lines["agi"] == 47000

def test_ltcg_netted_against_short_term_loss():
    f = compute_federal(FederalInput(wages=50000, capital_gain_lt=10000, capital_gain_st=-4000), RES)
    assert f.lines["capital_gain"] == 6000

def test_ltcg_zero_bracket():
    f = compute_federal(FederalInput(wages=30000, capital_gain_lt=10000), RES)
    assert f.lines["tax"] == 1475             # Tax Table on 14,250 ordinary; gains at 0%

def test_tips_overtime_schedule_1a():
    f = compute_federal(FederalInput(wages=60000, qualified_tips=3000, qualified_overtime=2000), RES)
    assert f.lines["sched1a_total"] == 5000 and f.lines["taxable_income"] == 60000 - 15750 - 5000

def test_salt_cap_itemized():
    f = compute_federal(FederalInput(wages=400000, state_income_tax_paid=50000, charitable=5000), RES)
    assert f.lines["deduction_type"] == "itemized" and f.lines["deduction"] == 45000

def test_niit_high_income():
    f = compute_federal(FederalInput(wages=250000, interest=20000), RES)
    assert f.lines["niit"] == round(0.038 * 20000)

def test_china_resident_alien_saving_clause():
    res = determine_residency(citizen=False, green_card=False, visa="F-1", first_entry_year=2019,
                              days_current=365, days_prior1=365, days_prior2=365)
    f = compute_federal(FederalInput(wages=30000, country="China", is_student=True), res)
    assert f.form == "1040" and f.lines["wages"] == 25000 and "Form 8833" in f.schedules


# ---------- federal: nonresident aliens ----------
def nra(visa="F-1", first=2023):
    return determine_residency(citizen=False, green_card=False, visa=visa, first_entry_year=first, days_current=365)

def test_nra_india_std_deduction_and_interest_not_taxed():
    f = compute_federal(FederalInput(wages=45000, fed_withholding=4200, interest=120, country="India",
                                     is_student=True, days_present=365), nra())
    L = f.lines
    assert f.form == "1040-NR" and L["taxable_interest"] == 0
    assert (L["agi"], L["deduction"], L["taxable_income"], L["tax"], L["refund"]) == (45000, 15750, 29250, 3275, 925)

def test_nra_china_5000_exemption():
    f = compute_federal(FederalInput(wages=30000, country="China", is_student=True), nra())
    assert f.lines["wages"] == 25000 and f.lines["treaty_exempt_income"] == 5000
    assert f.lines["deduction"] == 0 and f.lines["tax"] == 2765
    assert "Schedule OI (Form 1040-NR)" in f.schedules and "Form 8833" not in f.schedules

def test_nra_china_exemption_already_on_1042s_not_double_counted():
    f = compute_federal(FederalInput(wages=25000, comp_1042s=5000, country="China", is_student=True), nra())
    assert f.lines["wages"] == 25000 and f.lines["treaty_exempt_income"] == 5000

def test_nra_itemizes_state_tax():
    f = compute_federal(FederalInput(wages=30000, state_income_tax_paid=900, charitable=100, country="Brazil"), nra())
    assert f.lines["deduction"] == 1000 and f.lines["taxable_income"] == 29000

def test_nra_mfj_forced_mfs_hoh_forced_single():
    assert compute_federal(FederalInput(filing_status="mfj", wages=50000), nra()).filing_status == "mfs"
    assert compute_federal(FederalInput(filing_status="hoh", wages=50000), nra()).filing_status == "single"

def test_nra_no_eitc_no_ctc():
    f = compute_federal(FederalInput(wages=20000, qualifying_children=2, country="China", is_student=True), nra())
    assert f.lines["ctc_odc"] == 0 and f.lines["eitc"] == 0

def test_nra_dividends_and_capital_gains_on_schedule_nec():
    f = compute_federal(FederalInput(wages=20000, dividends=500, capital_gain_st=1000, country="India",
                                     is_student=True, days_present=300), nra())
    L = f.lines
    assert L["ordinary_dividends"] == 0 and L["capital_gain"] == 0
    assert L["nec_tax"] == round(500 * 0.25 + 1000 * 0.30)      # India treaty dividend rate 25%
    assert L["total_tax"] == L["tax"] + L["nec_tax"]

def test_nra_capital_gains_not_taxed_under_183_days():
    f = compute_federal(FederalInput(wages=20000, capital_gain_st=1000, days_present=120), nra())
    assert f.lines["nec_tax"] == 0

def test_nra_self_employment_taxed_without_se_tax():
    f = compute_federal(FederalInput(se_income=10000, state_income_tax_paid=0), nra())
    assert f.lines["total_income"] == 10000 and f.lines["se_tax"] == 0

def test_nra_1042s_withholding_is_a_payment():
    f = compute_federal(FederalInput(wages=10000, withholding_1042s=300), nra())
    assert f.lines["withholding_total"] == 300

def test_treaty_canada_threshold():
    t = apply_treaty("Canada", is_student=False, wages=9000, scholarship=0)
    assert t["wage_exempt"] == 9000 and not t["form_8833_required"]
    assert apply_treaty("Canada", is_student=False, wages=20000, scholarship=0)["wage_exempt"] == 0

def test_treaty_country_alias():
    assert apply_treaty("korea", is_student=True, wages=5000, scholarship=0)["wage_exempt"] == 2000


# ---------- dual status ----------
def test_dual_status_no_standard_deduction():
    res = determine_residency(citizen=False, green_card=False, visa="H-1B", first_entry_year=2025,
                              days_current=200, first_nonexempt_day="2025-06-15")
    f = compute_federal(FederalInput(filing_status="mfj", wages=50000, state_income_tax_paid=0), res)
    assert f.form == "1040 (Dual-Status)" and f.filing_status == "mfs"
    assert f.lines["deduction"] == 0 and f.lines["eitc"] == 0


# ---------- California ----------
def test_ca_540_basic():
    fi = FederalInput(wages=60000, fed_withholding=6000)
    ca = compute_california(CAInput(ca_withholding=2500, fed_input=fi), compute_federal(fi, RES))
    assert ca.form == "540" and ca.lines["taxable_income"] == 54294
    assert ca.lines["tax"] == 1793 and ca.lines["total_tax"] == 1640 and ca.lines["refund"] == 860

def test_ca_adds_back_treaty_and_nra_interest():
    fi = FederalInput(wages=30000, interest=200, country="China", is_student=True)
    ca = compute_california(CAInput(fed_input=fi), compute_federal(fi, nra()))
    assert ca.lines["ca_agi"] == 30200 and ca.lines["total_tax"] == 226

def test_ca_540nr_method():
    fi = FederalInput(wages=100000)
    ca = compute_california(CAInput(full_year_resident=False, ca_source_income=50000, fed_input=fi),
                            compute_federal(fi, RES))
    assert ca.form == "540NR" and ca.lines["ca_tax_rate"] == 0.0552
    assert ca.lines["ca_taxable_income"] == 47147 and ca.lines["total_tax"] == 2526

def test_ca_renters_credit():
    fi = FederalInput(wages=40000)
    ca = compute_california(CAInput(renter=True, fed_input=fi), compute_federal(fi, RES))
    assert ca.lines["renters_credit"] == 60

def test_ca_renters_credit_over_limit():
    fi = FederalInput(wages=60000)
    ca = compute_california(CAInput(renter=True, fed_input=fi), compute_federal(fi, RES))
    assert ca.lines["renters_credit"] == 0


# ---------- interview ----------
def test_safe_evaluator():
    assert evaluate("answers.get('a') == 'yes' and answers.get('b') in ['x', 'y']", {"a": "yes", "b": "y"})
    with pytest.raises(Exception):
        evaluate("__import__('os').system('echo hi')", {})

def test_interview_skips_residency_questions():
    ids = [q["id"] for q in next_questions({}, limit=50)]
    assert "citizen" not in ids and "visa" not in ids and ids[0] == "multi_employer"

def test_interview_nra_hides_dependents_and_tuition():
    ids = [q["id"] for q in next_questions({"_residency": "nonresident"}, limit=50)]
    assert "has_dependents" not in ids and "tuition_paid" not in ids and "has_1042s" in ids

def test_progress():
    p = progress({"multi_employer": "no"})
    assert 0 < p["pct"] < 100
