"""End-to-end API test: F-1 India student, $45k wages, CA full-year."""
import os
os.environ["DATABASE_URL"] = "sqlite:///./test_api.db"
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_full_journey():
    # register + auth
    r = client.post("/auth/register", json={"email": "sai@test.com", "password": "password123", "full_name": "Sai"})
    assert r.status_code == 200, r.text
    tok = {"Authorization": f"Bearer {r.json()['access_token']}"}

    # login works too
    r = client.post("/auth/login", data={"username": "sai@test.com", "password": "password123"})
    assert r.status_code == 200

    # create return
    rid = client.post("/returns", headers=tok).json()["id"]

    # residency profile: F-1 India, year 3 -> NRA exempt
    r = client.put(f"/returns/{rid}/profile", headers=tok, json={
        "citizen": False, "green_card": False, "visa": "F-1", "country": "India",
        "first_entry_year": 2023, "days_current": 365, "days_prior1": 365,
        "days_prior2": 120, "is_student": True})
    res = r.json()["residency"]
    assert res["status"] == "nonresident" and res["form_8843_required"]

    # adaptive interview
    r = client.put(f"/returns/{rid}/answers", headers=tok,
                   json={"answers": {"citizen": "no", "green_card": "no", "_residency": "nonresident"}})
    assert r.json()["progress"]["pct"] > 0

    # income
    r = client.put(f"/returns/{rid}/income", headers=tok, json={
        "filing_status": "single",
        "w2s": [{"employer": "Platinum Finishing", "wages": 45000,
                 "fed_withholding": 4200, "state_withholding": 1400}],
        "interest": 120, "student_loan_interest": 0})
    assert r.json()["ok"]

    # calculate
    out = client.post(f"/returns/{rid}/calculate", headers=tok).json()
    fed, ca = out["federal"], out["state"]
    assert fed["form"] == "1040-NR"
    assert fed["lines"]["12_deduction"] == 15750          # India treaty std deduction
    assert ca["form"] == "540"
    assert "Form 8843 — Statement for Exempt Individuals" in out["checklist"]
    # expected federal: taxable = 45120-15750 = 29370
    # tax = 1192.50 + (29370-11925)*.12 = 3285.90 -> 3286
    assert fed["lines"]["15_taxable_income"] == 29370
    assert fed["lines"]["16_tax"] == 3286
    assert fed["lines"]["refund"] == 4200 - 3286

    # unauthorized access blocked
    r2 = client.post("/auth/register", json={"email": "other@test.com", "password": "password123"})
    tok2 = {"Authorization": f"Bearer {r2.json()['access_token']}"}
    assert client.post(f"/returns/{rid}/calculate", headers=tok2).status_code == 404
