"""Supplemental federal forms: each is generated when needed and carries the computed amounts.
All people and numbers here are made up."""
import pymupdf
from app.api.returns import run_calculation
from app.pdf.forms import build_package

TP = {"first_name": "Test", "last_name": "Filer", "ssn": "123-45-6789", "address": "1 Main St",
      "city": "San Jose", "state": "CA", "zip": "95110", "foreign_country": "India"}


class _R:
    def __init__(self, profile, income):
        self.profile = dict(profile, taxpayer=TP); self.income = income; self.tax_year = 2025


def _pkg(profile, income):
    r = _R(profile, income)
    res = run_calculation(r)
    doc = pymupdf.open("pdf", build_package(TP, r.profile, res))
    return res, doc


def _form(doc, marker):
    for p in list(doc)[1:]:
        t = " ".join(p.get_text().split())
        if marker in t:
            return t
    raise AssertionError(f"no page containing {marker!r}")


def _forms(res):
    return res["federal"]["schedules"]


def test_itemized_high_earner_gets_a_8959_8960_and_3():
    income = {"state": "CA", "w2s": [
        {"employer": "Alpha Inc", "ein": "11-1111111", "wages": 160000, "medicare_wages": 160000, "medicare_tax": 2320,
         "ss_tax": 9920, "fed_withholding": 30000, "state": "CA", "state_withholding": 12000},
        {"employer": "Beta LLC", "ein": "22-2222222", "wages": 90000, "medicare_wages": 90000, "medicare_tax": 1305,
         "ss_tax": 5580, "fed_withholding": 15000, "state": "CA", "state_withholding": 6000}],
        "interest": 4000, "dividends": 6000, "qualified_dividends": 5000,
        "mortgage_interest": 18000, "real_estate_tax": 9000, "charitable": 3000}
    res, doc = _pkg({"citizen": True}, income)
    L = res["federal"]["lines"]
    # SALT: 12,000 + 6,000 + 9,000 = 27,000 (under the 40,000 cap); itemized 27,000 + 18,000 + 3,000 = 48,000
    assert L["deduction_type"] == "itemized" and L["sa_total"] == 48000
    sa = _form(doc, "SCHEDULE A")
    assert "48,000" in sa and "18,000" in sa and "27,000" in sa
    # Additional Medicare: (250,000 - 200,000) x 0.9% = 450; NIIT: 3.8% x min(10,000, 260,000 - 200,000) = 380
    assert L["addl_medicare"] == 450 and L["niit"] == 380
    assert "450" in _form(doc, "Form 8959") and "380" in _form(doc, "Form 8960")
    # excess Social Security: 9,920 + 5,580 - 10,918.20 = 4,581.80 -> 4,582 on Schedule 3 line 11
    assert L["excess_ss_credit"] == 4582 and "4,582" in _form(doc, "SCHEDULE 3")
    assert "Schedule A" not in " ".join(i for i in res["checklist"] if "not generated" in i)


def test_self_employment_schedule_se():
    res, doc = _pkg({"citizen": True}, {"state": "TX", "w2s": [{"wages": 20000}], "se_income": 30000})
    L = res["federal"]["lines"]
    # 30,000 x 92.35% = 27,705; SE tax 15.3% = 4,238.87 -> 4,239; half 2,119
    assert L["se_tax"] == 4239 and L["adj_half_se"] == 2119
    se = _form(doc, "SCHEDULE SE")
    assert "27,705" in se and "4,239" in se and "2,119" in se


def test_senior_schedule_1a_and_payment_voucher():
    res, doc = _pkg({"citizen": True}, {"state": "TX", "age": 67, "w2s": [{"wages": 90000, "fed_withholding": 1000}]})
    L = res["federal"]["lines"]
    assert L["sched1a_senior"] == 6000 - round(15000 * 0.06)   # 5,100
    s1a = _form(doc, "Enhanced Deduction for Seniors")
    assert "5,100" in s1a
    assert L["owed"] > 0
    assert "1040-V" in _form(doc, "Payment Voucher")


def test_nonresident_itemized_schedule_a_nr():
    profile = {"visa": "F-1", "country": "Brazil", "first_entry_year": 2023, "days_current": 365,
               "days_prior1": 365, "days_prior2": 120, "is_student": True}
    res, doc = _pkg(profile, {"state": "CA", "w2s": [{"wages": 30000, "state": "CA", "state_withholding": 900}],
                              "charitable": 200})
    assert res["federal"]["form"] == "1040-NR"
    sa = _form(doc, "(Form 1040-NR)")
    assert "1,100" in _form(doc, "Itemized Deductions")


def test_resident_alien_china_treaty_form_8833():
    profile = {"visa": "H-1B", "country": "China", "first_entry_year": 2019, "days_current": 365,
               "days_prior1": 365, "days_prior2": 365, "is_student": True}
    res, doc = _pkg(profile, {"state": "CA", "w2s": [{"employer": "Gamma Corp", "wages": 60000}]})
    if "Form 8833" in _forms(res):
        t = _form(doc, "Treaty-Based Return Position Disclosure")
        assert "China" in t and "Gamma Corp" in t


FAMILY = {"filing_status": "mfj", "state": "TX",
          "w2s": [{"employer": "Delta Co", "wages": 80000, "fed_withholding": 5000, "ss_tax": 4960, "medicare_tax": 1160}],
          "dependents": [{"first_name": "Kid", "last_name": "One", "ssn": "111-22-3333", "relationship": "Son", "credit": "ctc"},
                         {"first_name": "Kid", "last_name": "Two", "ssn": "111-22-4444", "relationship": "Daughter", "credit": "ctc"}],
          "interest_payers": [{"name": "Chase Bank", "amount": 1200}, {"name": "Ally Bank", "amount": 800}],
          "foreign_accounts": True, "fbar_required": True, "foreign_account_countries": "India",
          "st_proceeds": 10000, "st_basis": 12000, "lt_proceeds": 20000, "lt_basis": 15000,
          "business": {"description": "Software consulting", "code": "541510", "name": "Test Consulting",
                       "gross_receipts": 12000, "supplies": 1000, "meals_total": 400, "other_expenses": 300,
                       "other_description": "Software subscriptions"}}


def test_family_dependents_schedules_b_c_d_8812():
    res, doc = _pkg({"citizen": True}, FAMILY)
    L = res["federal"]["lines"]
    forms = _forms(res)
    for f in ("Schedule B", "Schedule C", "Schedule D", "Schedule 8812", "Schedule SE"):
        assert f in forms, f
    # interest from the payer list; capital: -2,000 short-term + 5,000 long-term = 3,000
    assert L["taxable_interest"] == 2000 and L["capital_gain"] == 3000
    # Schedule C: 12,000 - (1,000 + 50% x 400 + 300) = 10,500
    assert L["sched1_business"] == 10500
    sb = _form(doc, "SCHEDULE B")
    assert "Chase Bank" in sb and "1,200" in sb and "India" in sb
    sc = _form(doc, "SCHEDULE C")
    assert "Software consulting" in sc and "5 4 1 5 1 0" in sc and "10,500" in sc
    assert "Software subscriptions" in _form(doc, "Other Expenses")       # Part V on page 2
    sd = _form(doc, "SCHEDULE D")
    assert "20,000" in sd and "15,000" in sd and "(2,000)" in sd
    assert "3,000" in _form(doc, "Summary")                                # line 16, page 2
    s8 = _form(doc, "Credits for Qualifying Children")
    assert "4,400" in s8                                    # 2 x $2,200
    f1040 = _form(doc, "U.S. Individual Income Tax Return")
    assert "Kid" in f1040 and "Son" in f1040
    assert "1 1 1 2 2 3 3 3 3" in f1040                                   # full 9-digit SSN in the comb boxes
    # no leftover "attach yourself" items for these forms
    assert not any(m in " ".join(res["checklist"]) for m in ("Form 8949",))


def test_three_children_part_ii_b():
    inc = {"filing_status": "mfj", "state": "TX",
           "w2s": [{"wages": 30000, "ss_tax": 1860, "medicare_tax": 435}],
           "qualifying_children": 3}
    from app.api.returns import run_calculation
    L = run_calculation(_R({"citizen": True}, inc))["federal"]["lines"]
    S = L["s8812"]
    # tax 0, so line 16a = 6,600; 16b = 5,100; line 17 = 5,100; line 20 = 15% x 27,500 = 4,125 < 5,100 -> Part II-B
    assert S["line17"] == 5100 and S["line20"] == 4125 and "line25" in S
    # line 25 = max(0, FICA 2,295 - EITC) = 0, so ACTC = line 20
    assert L["actc"] == 4125


def test_dependent_ssn_masked_in_api_and_kept_on_save():
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app, headers={"X-TaxPrep": "1"})
    c.post("/auth/register", json={"email": "deps@test.com", "password": "password123"})
    rid = c.post("/returns").json()["id"]
    c.put(f"/returns/{rid}/income", json={"dependents": FAMILY["dependents"]})
    got = c.get(f"/returns/{rid}").json()["income"]
    assert got["dependents"][0]["ssn"] == "***-**-3333"
    c.put(f"/returns/{rid}/income", json=got)              # browser sends the masked values back
    from app.db.session import SessionLocal
    from app.db.models import TaxReturn
    db = SessionLocal()
    assert db.query(TaxReturn).get(rid).income["dependents"][0]["ssn"] == "111-22-3333"
    db.close()
