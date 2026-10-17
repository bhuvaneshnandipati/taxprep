"""Official-form package tests: the filled agency PDFs must carry the computed values on the right lines."""
import pymupdf, pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.returns import run_calculation
from app.pdf.forms import build_package
from app.pdf.fill import fill_pdf, template_path

TP = {"first_name": "Sai", "middle_initial": "K", "last_name": "Reddy", "ssn": "123-45-6789",
      "address": "100 College Ave", "apt": "4B", "city": "Berkeley", "state": "CA", "zip": "94704",
      "occupation": "Student", "date_of_birth": "2000-05-01", "school": "UC Berkeley"}


class _R:
    def __init__(self, profile, income):
        self.profile = dict(profile, taxpayer=TP); self.income = income; self.tax_year = 2025


def _pkg(profile, income):
    r = _R(profile, income)
    res = run_calculation(r)
    doc = pymupdf.open("pdf", build_package(TP, r.profile, res))
    return res, doc


def _page(doc, marker):
    for p in list(doc)[1:]:          # page 0 is the generated cover sheet
        t = p.get_text()
        if marker in t:
            return t
    raise AssertionError(f"page with {marker!r} not found")


def _value_near(page_text: str, value: str) -> bool:
    return value in page_text


INDIA = ({"visa": "F-1", "country": "India", "first_entry_year": 2023, "days_current": 365, "days_prior1": 365,
          "days_prior2": 120, "is_student": True, "visa_by_year": {"2023": "F-1", "2024": "F-1"}},
         {"w2s": [{"employer": "UC", "wages": 45000, "fed_withholding": 4200, "state": "CA",
                   "state_withholding": 1400}], "interest": 120, "state": "CA"})


def test_india_nra_package_uses_official_forms():
    res, doc = _pkg(*INDIA)
    cover = doc[0].get_text()
    assert "SYNTHETIC TEST PREVIEW - DO NOT FILE" in cover
    assert "Where and when to mail" not in cover
    assert "Sign and date each return" not in cover
    titles = [p.get_text()[:120] for p in doc]
    assert any("1040-NR" in t and "Nonresident Alien Income Tax Return" in t for t in titles)
    assert any("SCHEDULE OI" in t for t in titles)
    assert any("Form 8843" in t for t in titles)
    assert any("Form 540 2025 Side 1" in t for t in titles)
    p1 = _page(doc, "U.S. Nonresident Alien Income Tax Return")
    assert "45,000" in p1 and "Reddy" in p1 and "100 College Ave" in p1
    p2 = _page(doc, "Amount from line 11a")
    for v in ("15,750", "29,250", "3,275", "4,200", "925"):
        assert v in p2, v
    ca2 = _page(doc, "Side 2 Form 540 2025")
    assert "45120" in ca2 and "39414" in ca2          # CA AGI incl. interest; taxable = 45,120 - 5,706
    f8843 = _page(doc, "Statement for Exempt Individuals")
    assert "365" in f8843 and "India" in f8843
    assert doc.page_count == 1 + 2 + 1 + 2 + 6       # cover, 1040-NR, OI, 8843 (form pages only), 540


def test_china_treaty_on_line_1k_and_schedule_oi():
    res, doc = _pkg({"visa": "F-1", "country": "China", "first_entry_year": 2022, "days_current": 300,
                     "is_student": True, "treaty_prior_months": 24},
                    {"w2s": [{"wages": 30000, "fed_withholding": 2500}], "state": "TX"})
    p1 = _page(doc, "U.S. Nonresident Alien Income Tax Return")
    assert "25,000" in p1 and "5,000" in p1
    oi = _page(doc, "SCHEDULE OI")
    assert "20(c)" in oi and "China" in oi and "24" in oi


def test_dual_status_stamp_and_statement():
    res, doc = _pkg({"visa": "H-1B", "country": "Brazil", "first_entry_year": 2025, "days_current": 200,
                     "first_nonexempt_day": "2025-06-15"},
                    {"w2s": [{"wages": 90000, "fed_withholding": 12000, "state": "NY", "state_withholding": 4000}],
                     "state": "NY", "wages_nr_period": 0})
    assert res["federal"]["form"] == "1040 (Dual-Status)"
    assert "DUAL-STATUS RETURN" in doc[1].get_text()
    assert any("Dual-Status Statement" in p.get_text() for p in doc)
    it201 = _page(doc, "Resident Income Tax Return")
    assert "90000" in _page(doc, "Federal income and adjustments")


def test_nec_schedule_for_nra_dividends():
    res, doc = _pkg({"visa": "F-1", "country": "India", "first_entry_year": 2024, "days_current": 300,
                     "is_student": True},
                    {"w2s": [{"wages": 20000}], "dividends": 400, "capital_gain_st": 1000, "state": "TX"})
    nec = _page(doc, "SCHEDULE NEC")
    assert "400" in nec and "1,000" in nec and "400" in nec and str(round(400 * .25 + 300)) in nec


def test_fill_rejects_unknown_field():
    with pytest.raises(KeyError):
        fill_pdf(template_path(2025, "f1040.pdf"), {"no_such_field": "1"})


def test_schedule_2_maps_each_tax_to_its_official_line(tmp_path):
    from app.pdf.official import schedule_2
    fed = {"lines": {"se_tax": 1234, "addl_medicare": 567, "niit": 890, "other_taxes": 2691}}
    doc = schedule_2(2025, TP, fed)
    path = tmp_path / "schedule-2.pdf"
    doc.save(path)
    with pymupdf.open(path) as saved:
        assert "Sai K Reddy" in saved[0].get_text()
        for page, y, amount in [(0, 468, "1,234"), (0, 606, "567"),
                                (0, 624, "890"), (1, 582, "2,691")]:
            assert amount in saved[page].get_text(clip=pymupdf.Rect(490, y, 577, y + 16))
        assert all(not list(p.widgets()) for p in saved)


def test_schedule_2_in_package_keeps_supporting_form_warning():
    _, doc = _pkg({"citizen": True, "days_current": 365},
                  {"se_income": 30000, "state": "TX"})
    text = "\n".join(p.get_text() for p in doc)
    assert "SCHEDULE 2" in text
    assert "Not generated — complete and attach yourself: Schedule 2" not in text
    assert "Schedule SE" in text


def test_api_pdf_endpoint():
    c = TestClient(app)
    tok = {"Authorization": "Bearer " + c.post("/auth/register", json={"email": "pdf@test.com",
           "password": "password123"}).json()["access_token"]}
    rid = c.post("/returns", headers=tok).json()["id"]
    assert c.get(f"/returns/{rid}/package.pdf", headers=tok).status_code == 400
    c.put(f"/returns/{rid}/taxpayer", headers=tok, json=TP)
    c.put(f"/returns/{rid}/profile", headers=tok, json=INDIA[0])
    c.put(f"/returns/{rid}/income", headers=tok, json=INDIA[1])
    c.post(f"/returns/{rid}/calculate", headers=tok)
    r = c.get(f"/returns/{rid}/package.pdf", headers=tok)
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert pymupdf.open("pdf", r.content).page_count >= 10
