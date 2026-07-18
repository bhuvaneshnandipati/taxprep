"""Engine tests — expected values hand-computed from TY2025 rules."""
import pytest
from app.engines.residency import determine_residency
from app.engines.federal import compute_federal, FederalInput, marginal_tax
from app.engines.california import compute_california, CAInput
from app.engines.rules_loader import load_rules
from app.engines.interview import next_questions, progress
from app.engines.treaty import apply_treaty


# ---------- residency ----------
def test_citizen():
    r = determine_residency(citizen=True, green_card=False)
    assert r.status == "citizen" and r.form == "1040"

def test_green_card():
    r = determine_residency(citizen=False, green_card=True)
    assert r.status == "resident"

def test_f1_exempt_year4():
    r = determine_residency(citizen=False, green_card=False, visa="F-1",
                            first_entry_year=2022, days_current=365)
    assert r.status == "nonresident" and r.form_8843_required

def test_f1_year6_spt_met():
    r = determine_residency(citizen=False, green_card=False, visa="F-1",
                            first_entry_year=2019, days_current=365,
                            days_prior1=365, days_prior2=365)
    assert r.status == "resident"

def test_h1b_spt_not_met():
    r = determine_residency(citizen=False, green_card=False, visa="H-1B",
                            first_entry_year=2025, days_current=100)
    assert r.status == "nonresident"  # 100 < 183


# ---------- federal ----------
RES_RESIDENT = determine_residency(citizen=True, green_card=False)

def test_marginal_tax_single_60k_taxable():
    # taxable 44,250: 11,925*.10 + (44,250-11,925)*.12 = 1192.50 + 3879.00 = 5071.50
    assert marginal_tax(44250, load_rules("federal")["brackets"]["single"]) == pytest.approx(5071.50)

def test_single_w2_only():
    f = compute_federal(FederalInput(filing_status="single", wages=60000, fed_withholding=6000), RES_RESIDENT)
    assert f.lines["11_agi"] == 60000
    assert f.lines["12_deduction"] == 15750
    assert f.lines["15_taxable_income"] == 44250
    assert f.lines["16_tax"] == 5072   # rounded 5071.50
    assert f.lines["refund"] == 6000 - 5072

def test_ctc_two_kids():
    f = compute_federal(FederalInput(filing_status="mfj", wages=120000, fed_withholding=10000,
                                     qualifying_children=2), RES_RESIDENT)
    assert f.lines["19_ctc_odc"] == 4400   # 2 x 2200, no phaseout, tax exceeds credit

def test_actc_low_income():
    # tax is small; refundable portion limited by 15% of (earned - 2500)
    f = compute_federal(FederalInput(filing_status="hoh", wages=25000, qualifying_children=2), RES_RESIDENT)
    assert f.lines["28_actc"] > 0
    assert f.lines["28_actc"] <= 2 * 1700

def test_student_loan_phaseout_gone():
    f = compute_federal(FederalInput(filing_status="single", wages=120000,
                                     student_loan_interest=2500), RES_RESIDENT)
    assert f.lines["10_adjustments"] == 0   # MAGI 120k > 100k ceiling

def test_se_tax():
    f = compute_federal(FederalInput(filing_status="single", se_income=50000), RES_RESIDENT)
    net = 50000 * 0.9235
    expected = net * 0.124 + net * 0.029
    assert f.lines["23_other_taxes"] == round(expected)

def test_ltcg_zero_bracket():
    f = compute_federal(FederalInput(filing_status="single", wages=30000,
                                     capital_gain_lt=10000), RES_RESIDENT)
    # taxable = 40000-15750 = 24250; ordinary 14250, pref 10000 sits below 48350 -> 0% on gains
    ordinary = marginal_tax(14250, load_rules("federal")["brackets"]["single"])
    assert f.lines["16_tax"] == round(ordinary)

def test_niit_high_income():
    f = compute_federal(FederalInput(filing_status="single", wages=250000, interest=20000), RES_RESIDENT)
    assert any("8960" in e for e in f.explanations)


# ---------- NRA + treaty ----------
def nra(country="India", visa="F-1"):
    return determine_residency(citizen=False, green_card=False, visa=visa,
                               first_entry_year=2023, days_current=365)

def test_nra_india_std_deduction():
    f = compute_federal(FederalInput(filing_status="single", wages=40000, fed_withholding=4000,
                                     country="India", is_student=True), nra())
    assert f.form == "1040-NR"
    assert f.lines["12_deduction"] == 15750  # treaty Art. 21(2)

def test_nra_china_5000_exemption():
    f = compute_federal(FederalInput(filing_status="single", wages=30000, country="China",
                                     is_student=True), nra("China"))
    assert f.lines["1a_wages"] == 25000  # $5,000 exempt under Art. 20(c)
    assert f.lines["12_deduction"] == 0  # no std deduction, no itemized supplied

def test_nra_mfj_forced_mfs():
    f = compute_federal(FederalInput(filing_status="mfj", wages=50000, country="China",
                                     is_student=True), nra("China"))
    assert f.filing_status == "mfs"

def test_nra_no_eitc_no_ctc():
    f = compute_federal(FederalInput(filing_status="single", wages=20000, qualifying_children=2,
                                     country="China", is_student=True), nra("China"))
    assert f.lines["19_ctc_odc"] == 0 and f.lines["27_eitc"] == 0

def test_treaty_canada_threshold():
    t = apply_treaty("Canada", is_student=False, wages=9000, scholarship=0)
    assert t["wage_exempt"] == 9000 and t["form_8833_required"]
    t2 = apply_treaty("Canada", is_student=False, wages=20000, scholarship=0)
    assert t2["wage_exempt"] == 0


# ---------- California ----------
def test_ca_540_basic():
    fed = compute_federal(FederalInput(filing_status="single", wages=60000, fed_withholding=6000), RES_RESIDENT)
    ca = compute_california(CAInput(ca_withholding=2500), fed)
    assert ca.form == "540"
    assert ca.lines["19_taxable"] == 60000 - 5706
    # tax bands on 54,294: manually ~= 109.19+299.18+598.44+951.30+1174.66+... compute:
    expected = (10919*.01 + (25878-10919)*.02 + (40839-25878)*.04 + (54294-40839)*.06)
    assert ca.lines["31_tax"] == round(expected)

def test_ca_540nr_proration():
    fed = compute_federal(FederalInput(filing_status="single", wages=100000), RES_RESIDENT)
    ca_full = compute_california(CAInput(full_year_resident=True), fed)
    ca_half = compute_california(CAInput(full_year_resident=False, ca_income_ratio=0.5), fed)
    assert ca_half.form == "540NR"
    assert ca_half.lines["31_tax"] == pytest.approx(ca_full.lines["31_tax"] * 0.5, abs=1)

def test_ca_renters_credit():
    fed = compute_federal(FederalInput(filing_status="single", wages=40000), RES_RESIDENT)
    ca = compute_california(CAInput(renter=True), fed)
    assert any("renter" in e.lower() for e in ca.explanations)


# ---------- interview ----------
def test_interview_flow():
    q1 = next_questions({})
    assert q1[0]["id"] == "citizen"
    q2 = next_questions({"citizen": "no"})
    assert any(q["id"] == "green_card" for q in q2)
    q3 = next_questions({"citizen": "yes"})
    assert not any(q["id"] == "green_card" for q in q3)

def test_interview_nra_hides_dividends():
    qs = next_questions({"citizen": "no", "green_card": "no", "visa": "F-1", "country": "India",
                         "first_entry_year": 2023, "days_y0": 365, "days_y1": 365, "days_y2": 0,
                         "multi_employer": "no", "remote_states": "no", "has_interest": "no",
                         "_residency": "nonresident"}, limit=20)
    ids = [q["id"] for q in qs]
    assert "has_dividends" not in ids and "has_dependents" not in ids

def test_progress():
    p = progress({"citizen": "yes"})
    assert 0 < p["pct"] < 100
