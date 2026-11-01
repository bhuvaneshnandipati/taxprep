"""Tax-year update kit: draft gating, scaffolding and ledger validation.
Runs against a temporary copy of rules/ so the real repository is never changed."""
import shutil
import pytest
from app.engines import rules_loader
from tools.taxyear import common, new_year, validate


@pytest.fixture
def rules_copy(tmp_path, monkeypatch):
    dst = tmp_path / "rules"
    shutil.copytree(common.RULES / "2025", dst / "2025")
    monkeypatch.setattr(rules_loader, "RULES_DIR", dst)
    monkeypatch.setattr(common, "RULES", dst)
    monkeypatch.setattr(new_year, "RULES", dst)
    monkeypatch.setattr(validate, "RULES", dst)
    monkeypatch.setattr(common, "LOGS", tmp_path / "logs")
    monkeypatch.delenv("ALLOW_DRAFT_TAX_YEARS", raising=False)
    return dst


def test_2025_is_preview_and_available():
    assert rules_loader.year_status(2025) == "preview"
    assert 2025 in rules_loader.available_years()


def test_new_year_is_hidden_draft(rules_copy, monkeypatch):
    assert new_year.main(["--to", "2026"]) == 0
    assert rules_loader.year_status(2026) == "draft"
    assert rules_loader.available_years() == [2025]
    monkeypatch.setenv("ALLOW_DRAFT_TAX_YEARS", "1")
    assert rules_loader.available_years() == [2025, 2026]
    assert new_year.main(["--to", "2026"]) == 1  # never overwrites


def test_unknown_api_year_is_404():
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app, headers={"X-TaxPrep": "1"})
    assert c.get("/interview/rules/federal", params={"year": 2025}).status_code == 200
    assert c.get("/interview/rules/federal", params={"year": 1999}).status_code == 404


def test_ledger_blocks_release(rules_copy):
    new_year.main(["--to", "2026"])
    assert validate.main(["--year", "2026"]) == 0               # draft: OK with TODOs
    assert validate.main(["--year", "2026", "--target", "released"]) == 1
    # A YAML edit that is not mirrored in the ledger is an error even for drafts.
    fed = rules_copy / "2026" / "federal.yaml"
    fed.write_text(fed.read_text().replace("single: 15750, mfj: 31500", "single: 16100, mfj: 31500", 1))
    assert validate.main(["--year", "2026"]) == 1
    ledger = rules_copy / "2026" / "SOURCES.md"
    ledger.write_text(ledger.read_text().replace(
        "| federal | standard_deduction.single | 15750 | 15750 | TODO |  |  |  |",
        "| federal | standard_deduction.single | 15750 | 16100 | CHANGED | https://www.irs.gov/example | Sec. 4.01 | 2026-11-01 |"))
    assert validate.main(["--year", "2026"]) == 0


def test_missing_key_is_error(rules_copy):
    new_year.main(["--to", "2026"])
    fed = rules_copy / "2026" / "federal.yaml"
    fed.write_text("\n".join(l for l in fed.read_text().splitlines() if not l.startswith("additional_std_deduction")))
    assert validate.main(["--year", "2026"]) == 1
