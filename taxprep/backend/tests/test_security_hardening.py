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
    response = TestClient(app).get('/health')
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
