"""Data retention: audit log entries are purged after a fixed window so the
database doesn't grow unbounded. This is the only table without a natural
cap (tax returns/documents belong to a user and are bounded by usage).
"""
import calendar
from datetime import datetime
from sqlalchemy.orm import Session
from ..db.models import AuditLog

AUDIT_RETENTION_MONTHS = 5

def months_ago(n: int, now: datetime | None = None) -> datetime:
    now = now or datetime.utcnow()
    month, year = now.month - n, now.year
    while month <= 0:
        month += 12
        year -= 1
    day = min(now.day, calendar.monthrange(year, month)[1])
    return now.replace(year=year, month=month, day=day)

def purge_audit_log(db: Session, months: int = AUDIT_RETENTION_MONTHS) -> int:
    cutoff = months_ago(months)
    q = db.query(AuditLog).filter(AuditLog.at < cutoff)
    count = q.count()
    if count:
        q.delete(synchronize_session=False)
        db.commit()
    return count
