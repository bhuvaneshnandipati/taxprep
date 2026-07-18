"""Audit log retention: 5-month window, opportunistic + manual purge."""
import os
from datetime import datetime, timedelta
from app.core.retention import months_ago, purge_audit_log, AUDIT_RETENTION_MONTHS

def test_months_ago_handles_year_rollover():
    now = datetime(2026, 2, 15)
    cutoff = months_ago(5, now)
    assert cutoff.year == 2025 and cutoff.month == 9 and cutoff.day == 15

def test_months_ago_clamps_day_overflow():
    now = datetime(2026, 3, 31)  # March 31 - 5 months = Oct 31, fine; test Feb edge instead
    cutoff = months_ago(6, datetime(2026, 8, 31))  # Aug 31 - 6mo = Feb 31 (invalid) -> clamp to Feb 28
    assert cutoff.year == 2026 and cutoff.month == 2 and cutoff.day == 28

def test_purge_removes_only_old_entries():
    os.environ["DATABASE_URL"] = "sqlite:///./test_retention.db"
    from app.db.session import SessionLocal, Base, engine
    from app.db.models import AuditLog
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.query(AuditLog).delete(); db.commit()
    old = datetime.utcnow() - timedelta(days=200)   # ~6.5 months old
    recent = datetime.utcnow() - timedelta(days=10)
    db.add(AuditLog(user_email="a@test.com", action="login", at=old))
    db.add(AuditLog(user_email="a@test.com", action="login", at=recent))
    db.commit()
    deleted = purge_audit_log(db)
    assert deleted == 1
    remaining = db.query(AuditLog).all()
    assert len(remaining) == 1 and remaining[0].at == recent
    db.close()

def test_admin_audit_endpoint_shape_and_purge_route():
    os.environ["DATABASE_URL"] = "sqlite:///./test_retention_api.db"
    os.environ["ADMIN_EMAILS"] = "boss2@test.com"
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    tok = {"Authorization": "Bearer " + c.post("/auth/register",
           json={"email": "boss2@test.com", "password": "password123"}).json()["access_token"]}
    out = c.get("/admin/audit", headers=tok).json()
    assert out["retention_months"] == AUDIT_RETENTION_MONTHS
    assert isinstance(out["entries"], list)
    purge = c.post("/admin/audit/purge", headers=tok).json()
    assert "deleted" in purge
    # the purge action itself should now appear in the log
    out2 = c.get("/admin/audit", headers=tok).json()
    assert any(e["action"] == "audit_purge" for e in out2["entries"])
