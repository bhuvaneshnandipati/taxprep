import os
import subprocess
import sys
from pathlib import Path
import pytest
import bcrypt
from app.core.security import hash_password, verify_password
from fastapi.testclient import TestClient
from app.main import app


def test_full_password_is_significant_and_old_hashes_work():
    prefix = 'a' * 72
    hashed = hash_password(prefix + 'one')
    assert verify_password(prefix + 'one', hashed)
    assert not verify_password(prefix + 'two', hashed)
    old = bcrypt.hashpw(b'oldpassword', bcrypt.gensalt()).decode()
    assert verify_password('oldpassword', old)
    assert not verify_password('oldpassword' + 'a' * 72, old)


@pytest.mark.parametrize('field', ['interest', 'capital_gain_lt', 'se_income'])
def test_money_rejects_nonfinite_values(field):
    from app.schemas import IncomeIn
    from pydantic import ValidationError
    for value in (float('inf'), float('-inf'), float('nan')):
        with pytest.raises(ValidationError):
            IncomeIn(**{field: value})


@pytest.mark.parametrize('missing', ['JWT_SECRET', 'DATA_KEY', 'DATABASE_URL', 'CORS_ORIGINS'])
def test_production_refuses_unsafe_configuration(missing):
    from cryptography.fernet import Fernet
    env = dict(os.environ, PRODUCTION='1', JWT_SECRET='x' * 48,
               DATA_KEY=Fernet.generate_key().decode(), DATABASE_URL='postgresql://test:test@localhost/test',
               CORS_ORIGINS='https://taxprep.example')
    env.pop(missing)
    result = subprocess.run([sys.executable, '-c', 'import app.core.config'], env=env,
                            capture_output=True, text=True, cwd=Path(__file__).resolve().parents[1])
    assert result.returncode != 0
    assert missing in result.stderr


def test_private_api_responses_are_not_cacheable():
    response = TestClient(app, headers={"X-TaxPrep": "1"}).get('/health')
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-content-type-options'] == 'nosniff'


@pytest.mark.parametrize('income,reason', [
    ({'age': 65}, 'Age 65+'),
    ({'age': 21, 'education_credit_type': 'aotc', 'tuition_paid': 4000}, 'AOTC'),
    ({'w2s': [{'wages': 250000, 'medicare_wages': 250000, 'medicare_tax': 4075}]}, 'Medicare'),
    ({'w2s': [{'wages': 180000, 'ss_tax': 11160}]}, 'Social Security'),
])
def test_unsupported_refund_scenarios_fail_closed(income, reason):
    from app.api.returns import run_calculation
    from types import SimpleNamespace
    row = SimpleNamespace(profile={'citizen': True}, income=income, tax_year=2025)
    with pytest.raises(ValueError, match=reason.replace('+', r'\+')):
        run_calculation(row)


def test_mixed_medicare_wages_fall_back_per_w2():
    from app.api.returns import run_calculation
    from types import SimpleNamespace
    row = SimpleNamespace(profile={'citizen': True}, tax_year=2025, income={
        'state': 'TX', 'w2s': [{'wages': 150000, 'medicare_wages': 150000}, {'wages': 100000}]})
    out = run_calculation(row)
    assert out['federal']['lines']['addl_medicare'] == 450


def test_qss_uses_200k_credit_and_medicare_thresholds():
    from app.engines.rules_loader import load_rules
    rules = load_rules('federal')
    assert rules['additional_medicare']['threshold']['qss'] == 200000
    assert rules['child_tax_credit']['phaseout_agi']['qss'] == 200000
    assert rules['niit']['magi_threshold']['qss'] == 250000

    from app.api.returns import run_calculation
    from types import SimpleNamespace
    out = run_calculation(SimpleNamespace(profile={'citizen': True}, tax_year=2025,
        income={'state': 'TX', 'filing_status': 'qss', 'qualifying_children': 1,
                'w2s': [{'wages': 250000}]}))
    assert out['federal']['lines']['addl_medicare'] == 450
    assert out['federal']['lines']['ctc_odc'] == 0



def test_applied_document_cannot_be_reopened_and_duplicated():
    from app.db.session import SessionLocal
    from app.db.models import Document
    client = TestClient(app, headers={"X-TaxPrep": "1"})
    response = client.post('/auth/register', json={'email': 'document.once@example.com', 'password': 'synthetic-password'})
    headers = {'Authorization': 'Bearer ' + response.json()['access_token']}
    rid = client.post('/returns', headers=headers).json()['id']
    with SessionLocal() as db:
        doc = Document(return_id=rid, filename='synthetic.txt', doc_type='W-2', status='reviewed',
                       extracted={'fields': {'wages': {'value': 1000}, 'employer': {'value': 'Synthetic'}}})
        db.add(doc); db.commit(); db.refresh(doc); did = doc.id
    url = f'/returns/{rid}/documents/{did}'
    assert client.post(url + '/apply', headers=headers).status_code == 200
    assert client.put(url, headers=headers, json={'wages': 2000}).status_code == 409
    assert client.post(url + '/apply', headers=headers).status_code == 409
    income = client.get(f'/returns/{rid}', headers=headers).json()['income']
    assert len(income['w2s']) == 1 and income['w2s'][0]['wages'] == 1000



def test_pdf_has_no_preview_stamp_and_courier_address():
    from app.api.returns import run_calculation
    from app.pdf.forms import build_package
    from types import SimpleNamespace
    import pymupdf
    row = SimpleNamespace(profile={'citizen': True}, tax_year=2025,
                          income={'state': 'NY', 'w2s': [{'wages': 45000, 'state': 'NY'}]})
    result = run_calculation(row)
    doc = pymupdf.open('pdf', build_package({'first_name': 'Test', 'last_name': 'Example'}, row.profile, result))
    assert 'DO NOT FILE' not in doc.metadata['title']
    assert not any('SYNTHETIC' in page.get_text() for page in doc)
    cover = " ".join(" ".join(p.get_text().split()) for p in doc[:2])
    assert "333 W. Pershing, Kansas City, MO 64108" in cover          # NY resident 1040 -> Kansas City
    assert "90 Cohoes Ave, Green Island, NY 12183-1515" in cover


# ---------------------------------------------------------------- sessions, lockout, invite-only, CSRF
def _client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app, headers={"X-TaxPrep": "1"})


def test_cookie_session_logout_and_csrf():
    from fastapi.testclient import TestClient
    from app.main import app
    c = _client()
    r = c.post("/auth/register", json={"email": "cookie@test.com", "password": "password123", "full_name": "C"})
    assert r.status_code == 200
    set_cookie = r.headers["set-cookie"].lower()
    assert "taxprep_session=" in set_cookie and "httponly" in set_cookie and "samesite=strict" in set_cookie
    assert c.get("/returns").status_code == 200                  # cookie alone authenticates
    # a cross-site form post carries the cookie but cannot add the custom header
    bare = TestClient(app); bare.cookies.update(c.cookies)
    assert bare.post("/returns").status_code == 403
    assert c.post("/auth/logout").status_code == 200
    assert c.get("/returns").status_code == 401                  # session is gone server-side


def test_login_lockout():
    from app.core.config import settings
    c = _client()
    c.post("/auth/register", json={"email": "lock@test.com", "password": "password123", "full_name": "L"})
    for _ in range(settings.MAX_FAILED_PER_EMAIL):
        assert c.post("/auth/login", data={"username": "lock@test.com", "password": "wrong-pass"}).status_code == 401
    # even the right password is refused while locked
    assert c.post("/auth/login", data={"username": "lock@test.com", "password": "password123"}).status_code == 429


def test_invite_only_registration(monkeypatch):
    from app.core.config import settings
    c = _client()
    monkeypatch.setattr(settings, "PRODUCTION", True)
    monkeypatch.setattr(settings, "REGISTRATION_EMAILS", [])
    assert c.post("/auth/register", json={"email": "x@test.com", "password": "password123"}).status_code == 403
    monkeypatch.setattr(settings, "REGISTRATION_EMAILS", ["family@test.com"])
    assert c.post("/auth/register", json={"email": "y@test.com", "password": "password123"}).status_code == 403
    assert c.post("/auth/register", json={"email": "Family@test.com", "password": "password123"}).status_code == 200


def test_idle_session_expires(monkeypatch):
    from app.core.config import settings
    c = _client()
    tok = c.post("/auth/register", json={"email": "idle@test.com", "password": "password123"}).json()["access_token"]
    monkeypatch.setattr(settings, "SESSION_IDLE_MINUTES", -1)
    assert c.get("/returns", headers={"Authorization": f"Bearer {tok}"}).status_code == 401


def test_delete_account_removes_everything():
    from app.db.session import SessionLocal
    from app.db.models import User, TaxReturn
    c = _client()
    c.post("/auth/register", json={"email": "gone@test.com", "password": "password123"})
    rid = c.post("/returns").json()["id"]
    assert c.delete("/auth/account").status_code == 200
    db = SessionLocal()
    assert db.query(User).filter_by(email="gone@test.com").first() is None
    assert db.query(TaxReturn).get(rid) is None
    db.close()
