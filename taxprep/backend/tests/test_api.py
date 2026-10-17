"""End-to-end API tests: register -> profile -> interview -> income -> calculate -> resume -> package."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _auth(email):
    r = client.post("/auth/register", json={"email": email, "password": "password123", "full_name": "T"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_full_journey_f1_india_ca():
    tok = _auth("sai@test.com")
    assert client.post("/auth/login", data={"username": "sai@test.com", "password": "password123"}).status_code == 200
    rid = client.post("/returns", headers=tok).json()["id"]

    r = client.put(f"/returns/{rid}/profile", headers=tok, json={
        "citizen": False, "green_card": False, "visa": "F-1", "country": "India",
        "first_entry_year": 2023, "days_current": 365, "days_prior1": 365,
        "days_prior2": 120, "is_student": True})
    body = r.json()
    assert body["residency"]["status"] == "nonresident" and body["residency"]["form_8843_required"]
    # interview never re-asks residency; server injected _residency
    ids = [q["id"] for q in body["next_questions"]]
    assert "citizen" not in ids and "has_1042s" in ids

    # client cannot override residency
    r = client.put(f"/returns/{rid}/answers", headers=tok,
                   json={"answers": {"has_interest": "yes", "_residency": "resident"}})
    assert r.json()["progress"]["pct"] > 0

    r = client.put(f"/returns/{rid}/income", headers=tok, json={
        "filing_status": "single",
        "w2s": [{"employer": "Platinum Finishing", "wages": 45000, "fed_withholding": 4200,
                 "state": "CA", "state_withholding": 1400}],
        "interest": 120})
    assert r.json()["ok"]

    out = client.post(f"/returns/{rid}/calculate", headers=tok).json()
    fed, ca = out["federal"], out["state"]
    assert fed["form"] == "1040-NR"
    assert fed["lines"]["deduction"] == 15750          # India treaty standard deduction
    assert fed["lines"]["taxable_income"] == 29250     # interest is not taxable to an NRA
    assert fed["lines"]["tax"] == 3275 and fed["lines"]["refund"] == 925
    assert ca["form"] == "540" and ca["lines"]["ca_agi"] == 45120   # CA taxes the interest
    assert any(i.startswith("Form 8843") for i in out["checklist"])
    assert "Austin, TX 73301-0215" in out["mailing"]["federal"]

    # resume: GET returns everything the wizard needs
    g = client.get(f"/returns/{rid}", headers=tok).json()
    assert g["profile"]["visa"] == "F-1" and g["income"]["w2s"][0]["wages"] == 45000
    assert g["result"]["federal"]["lines"]["refund"] == 925 and g["answers"]["_residency"] == "nonresident"

    # editing income invalidates the stale result
    client.put(f"/returns/{rid}/income", headers=tok, json={"w2s": [{"wages": 1000}]})
    assert client.get(f"/returns/{rid}", headers=tok).json()["result"] is None

    # unauthorized access blocked
    tok2 = _auth("other@test.com")
    assert client.post(f"/returns/{rid}/calculate", headers=tok2).status_code == 404
    assert client.get(f"/returns/{rid}", headers=tok2).status_code == 404
    assert client.delete(f"/returns/{rid}", headers=tok2).status_code == 404
    assert client.delete(f"/returns/{rid}", headers=tok).json()["ok"]


def test_fica_refund_flagged_for_exempt_student():
    tok = _auth("fica@test.com")
    rid = client.post("/returns", headers=tok).json()["id"]
    client.put(f"/returns/{rid}/profile", headers=tok, json={
        "visa": "F-1", "country": "Brazil", "first_entry_year": 2024, "days_current": 365, "is_student": True})
    client.put(f"/returns/{rid}/income", headers=tok, json={"state": "TX",
        "w2s": [{"wages": 20000, "fed_withholding": 1500, "ss_tax": 1240, "medicare_tax": 290}]})
    out = client.post(f"/returns/{rid}/calculate", headers=tok).json()
    assert any("Form 843" in i for i in out["checklist"])
    assert out["state"]["form"] == "none"


def test_validation_rejects_bad_input():
    tok = _auth("bad@test.com")
    rid = client.post("/returns", headers=tok).json()["id"]
    assert client.put(f"/returns/{rid}/income", headers=tok, json={"filing_status": "married"}).status_code == 422
    assert client.put(f"/returns/{rid}/income", headers=tok, json={"interest": -5}).status_code == 422
    assert client.put(f"/returns/{rid}/profile", headers=tok, json={"days_current": 400}).status_code == 422
    assert client.post(f"/returns/{rid}/calculate", headers=tok).status_code == 400


def test_unknown_rules_pack_404():
    assert client.get("/interview/rules/..%2Fsecrets").status_code == 404


def test_ssn_encrypted_at_rest():
    from app.db.session import SessionLocal
    from app.db.models import TaxReturn
    tok = _auth("enc@test.com")
    rid = client.post("/returns", headers=tok).json()["id"]
    client.put(f"/returns/{rid}/taxpayer", headers=tok, json={"first_name": "A", "last_name": "B", "ssn": "123-45-6789"})
    db = SessionLocal()
    stored = db.query(TaxReturn).get(rid).profile["taxpayer"]["ssn"]
    db.close()
    assert stored.startswith("enc:") and "6789" not in stored
    assert client.get(f"/returns/{rid}", headers=tok).json()["taxpayer"]["ssn"] == "123-45-6789"
