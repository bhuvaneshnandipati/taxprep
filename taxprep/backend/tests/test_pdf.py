"""PDF package tests: generate for NRA-India and resident scenarios, verify content."""
import io
import pdfplumber
from app.engines.residency import determine_residency
from app.engines.federal import compute_federal, FederalInput
from app.engines.california import compute_california, CAInput
from app.api.returns import build_checklist
from app.pdf.forms import build_package

TAXPAYER = {"first_name": "Sai", "last_name": "Kumar", "ssn": "123-45-6789",
            "address": "100 Main St", "city_state_zip": "Santa Rosa, CA 95401",
            "school": "Sonoma State University", "country": "India"}

def _result(fin, res, cain):
    fed = compute_federal(fin, res)
    ca = compute_california(cain, fed)
    return {"residency": res.__dict__,
            "federal": {"form": fed.form, "filing_status": fed.filing_status,
                        "lines": fed.lines, "explanations": fed.explanations, "treaty": fed.treaty},
            "state": {"state": "CA", "form": ca.form, "lines": ca.lines, "explanations": ca.explanations},
            "checklist": build_checklist(res, fed, ca)}

def _text(pdf_bytes):
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return [p.extract_text() or "" for p in pdf.pages]

def test_nra_india_package():
    res = determine_residency(citizen=False, green_card=False, visa="F-1",
                              first_entry_year=2023, days_current=365)
    result = _result(FederalInput(filing_status="single", wages=45000, fed_withholding=4200,
                                  interest=120, country="India", is_student=True), res,
                     CAInput(ca_withholding=1400))
    profile = {"visa": "F-1", "country": "India", "first_entry_year": 2023,
               "days_current": 365, "days_prior1": 365, "days_prior2": 120}
    pdf = build_package(TAXPAYER, profile, result)
    pages = _text(pdf)
    assert len(pages) == 4                       # cover, 1040-NR, 8843, 540
    assert "1040-NR" in pages[1]
    assert "29,370" in pages[1]                  # taxable income
    assert "8843" in pages[2]
    assert "540" in pages[3]
    assert any("Refund Summary" in p for p in pages)
    assert any("Austin, TX" in p for p in pages) # NR mailing address

def test_resident_package_no_8843():
    res = determine_residency(citizen=True, green_card=False)
    result = _result(FederalInput(filing_status="mfj", wages=150000, fed_withholding=18000,
                                  qualifying_children=2), res, CAInput(ca_withholding=6000))
    pdf = build_package(TAXPAYER, {}, result)
    pages = _text(pdf)
    assert len(pages) == 3                       # no 8843
    assert "1040" in pages[1] and "1040-NR" not in pages[1]
    assert any("4,400" in p for p in pages)      # CTC 2 x 2,200

def test_api_pdf_endpoint():
    import os
    os.environ["DATABASE_URL"] = "sqlite:///./test_pdf_api.db"
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    tok = {"Authorization": "Bearer " + c.post("/auth/register",
           json={"email": "pdf@test.com", "password": "password123"}).json()["access_token"]}
    rid = c.post("/returns", headers=tok).json()["id"]
    c.put(f"/returns/{rid}/profile", headers=tok, json={
        "citizen": False, "green_card": False, "visa": "F-1", "country": "India",
        "first_entry_year": 2023, "days_current": 365, "days_prior1": 365,
        "days_prior2": 120, "is_student": True})
    c.put(f"/returns/{rid}/taxpayer", headers=tok, json=TAXPAYER)
    c.put(f"/returns/{rid}/income", headers=tok, json={
        "filing_status": "single",
        "w2s": [{"employer": "PFS", "wages": 45000, "fed_withholding": 4200, "state_withholding": 1400}]})
    assert c.post(f"/returns/{rid}/calculate", headers=tok).status_code == 200
    r = c.get(f"/returns/{rid}/package.pdf", headers=tok)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert len(r.content) > 5000
