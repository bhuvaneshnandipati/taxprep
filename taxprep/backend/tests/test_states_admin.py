"""Phase 5 tests: state registry, NY engine, no-tax states, treaties, dual-status, admin RBAC."""
import os, pytest
from app.engines.residency import determine_residency
from app.engines.federal import compute_federal, FederalInput, marginal_tax
from app.engines.states.registry import compute_state, StateInput, NO_INCOME_TAX
from app.engines.rules_loader import load_rules
from app.engines.treaty import apply_treaty

RES = determine_residency(citizen=True, green_card=False)
FED = compute_federal(FederalInput(filing_status="single", wages=80000, fed_withholding=9000), RES)

def test_ny_it201():
    out = compute_state(StateInput(state="NY", withholding=4000), FED)
    assert out.form == "IT-201"
    taxable = 80000 - 8000
    assert out.lines["37_taxable"] == taxable
    assert out.lines["39_tax"] == round(marginal_tax(taxable, load_rules("newyork")["brackets"]["single"]))

def test_ny_it203_proration():
    full = compute_state(StateInput(state="NY"), FED)
    half = compute_state(StateInput(state="NY", full_year_resident=False, income_ratio=0.5), FED)
    assert half.form == "IT-203"
    assert half.lines["39_tax"] == pytest.approx(full.lines["39_tax"] * 0.5, abs=1)

def test_no_tax_state():
    out = compute_state(StateInput(state="TX", withholding=0), FED)
    assert out.form == "none" and "no state income tax" in out.explanations[0]

def test_unsupported_state():
    with pytest.raises(ValueError):
        compute_state(StateInput(state="OH"), FED)

def test_no_tax_set():
    assert {"TX", "FL", "WA", "NV", "AK", "SD", "WY", "TN", "NH"} <= NO_INCOME_TAX

def test_treaty_expansion():
    assert apply_treaty("Bangladesh", is_student=True, wages=20000, scholarship=0)["wage_exempt"] == 8000
    assert apply_treaty("Spain", is_student=True, wages=3000, scholarship=0)["wage_exempt"] == 3000
    assert apply_treaty("France", is_student=True, wages=10000, scholarship=4000)["scholarship_exempt"] == 4000
    assert apply_treaty("Brazil", is_student=True, wages=10000, scholarship=0)["wage_exempt"] == 0  # no treaty

def test_dual_status_flag():
    r = determine_residency(citizen=False, green_card=False, visa="H-1B",
                            first_entry_year=2025, days_current=200)
    assert r.status == "resident" and r.dual_status_possible

def test_admin_rbac_and_endpoints():
    os.environ["DATABASE_URL"] = "sqlite:///./test_admin.db"
    os.environ["ADMIN_EMAILS"] = "boss@test.com"
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    user_tok = {"Authorization": "Bearer " + c.post("/auth/register",
                json={"email": "pleb@test.com", "password": "password123"}).json()["access_token"]}
    admin_tok = {"Authorization": "Bearer " + c.post("/auth/register",
                 json={"email": "boss@test.com", "password": "password123"}).json()["access_token"]}
    assert c.get("/admin/users", headers=user_tok).status_code == 403
    users = c.get("/admin/users", headers=admin_tok).json()
    assert len(users) >= 2 and any(u["email"] == "pleb@test.com" for u in users)
    assert c.get("/admin/audit", headers=admin_tok).status_code == 200  # shape checked in test_retention.py
    assert c.get("/admin/documents/review-queue", headers=admin_tok).json() == []
    packs = c.get("/admin/rules", headers=admin_tok).json()
    assert "newyork" in packs["2025"] or "newyork" in packs.get(2025, [])
    pack = c.get("/admin/rules/2025/federal", headers=admin_tok).json()
    assert pack["year"] == 2025
    # promote user
    uid = [u for u in users if u["email"] == "pleb@test.com"][0]["id"]
    assert c.put(f"/admin/users/{uid}/role", headers=admin_tok, json={"role": "admin"}).status_code == 200
    assert c.get("/admin/users", headers=user_tok).status_code == 200

def test_calculate_with_ny():
    os.environ["DATABASE_URL"] = "sqlite:///./test_ny_api.db"
    os.environ.pop("ADMIN_EMAILS", None)
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    tok = {"Authorization": "Bearer " + c.post("/auth/register",
           json={"email": "ny@test.com", "password": "password123"}).json()["access_token"]}
    rid = c.post("/returns", headers=tok).json()["id"]
    c.put(f"/returns/{rid}/profile", headers=tok, json={"citizen": True, "green_card": False})
    c.put(f"/returns/{rid}/income", headers=tok, json={
        "filing_status": "single", "state": "NY",
        "w2s": [{"employer": "Acme NYC", "wages": 80000, "fed_withholding": 9000, "state_withholding": 4200}]})
    out = c.post(f"/returns/{rid}/calculate", headers=tok).json()
    assert out["state"]["form"] == "IT-201"
    assert any("New York Form IT-201" in i for i in out["checklist"])
    pdf = c.get(f"/returns/{rid}/package.pdf", headers=tok)
    assert pdf.status_code == 200 and len(pdf.content) > 4000
