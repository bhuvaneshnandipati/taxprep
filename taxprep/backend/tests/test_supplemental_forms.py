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
