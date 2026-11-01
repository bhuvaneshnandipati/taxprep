"""Passwords, server-side sessions and sign-in throttling.

Sessions are random opaque tokens. The browser gets them in an HttpOnly, Secure,
SameSite=Strict cookie (JavaScript can never read it); API clients and tests may
send the same token as `Authorization: Bearer`. Only the SHA-256 of a token is
stored. A session ends on sign-out, after SESSION_IDLE_MINUTES without use, or
SESSION_MAX_HOURS after sign-in.
"""
from datetime import datetime, timedelta, timezone
import base64, hashlib, secrets
import bcrypt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from .config import settings
from ..db.session import get_db

COOKIE = "taxprep_session"


def hash_password(pw: str) -> str:
    digest = base64.b64encode(hashlib.sha256(pw.encode()).digest())
    return "bcrypt-sha256:" + bcrypt.hashpw(digest, bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        if hashed.startswith("bcrypt-sha256:"):
            digest = base64.b64encode(hashlib.sha256(pw.encode()).digest())
            return bcrypt.checkpw(digest, hashed.removeprefix("bcrypt-sha256:").encode())
        # Preserve existing accounts, without accepting equivalent truncated passwords.
        if len(pw.encode()) > 72:
            return False
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except ValueError:
        return False


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(db: Session, email: str) -> str:
    from ..db.models import AuthSession
    token = secrets.token_urlsafe(32)
    now = _now()
    db.add(AuthSession(token_hash=_hash(token), user_email=email, created_at=now, last_seen=now))
    return token


def end_session(db: Session, token: str | None):
    from ..db.models import AuthSession
    if token:
        db.query(AuthSession).filter_by(token_hash=_hash(token)).delete()


def end_all_sessions(db: Session, email: str):
    from ..db.models import AuthSession
    db.query(AuthSession).filter_by(user_email=email).delete()


def request_token(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    return request.cookies.get(COOKIE)


def current_user_email(request: Request, db: Session = Depends(get_db)) -> str:
    from ..db.models import AuthSession
    token = request_token(request)
    s = db.query(AuthSession).filter_by(token_hash=_hash(token)).first() if token else None
    now = _now()
    if not s or now - s.last_seen > timedelta(minutes=settings.SESSION_IDLE_MINUTES) \
            or now - s.created_at > timedelta(hours=settings.SESSION_MAX_HOURS):
        if s:
            db.delete(s); db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Signed out. Please sign in again.")
    if now - s.last_seen > timedelta(minutes=1):      # sliding idle timeout, at most one write a minute
        s.last_seen = now; db.commit()
    return s.user_email


# ---------------------------------------------------------------- sign-in throttling
def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return (fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "")) or "?"


def check_throttle(db: Session, email: str, ip: str):
    from ..db.models import LoginAttempt
    since = _now() - timedelta(minutes=settings.LOCKOUT_MINUTES)
    q = db.query(LoginAttempt).filter(LoginAttempt.at >= since, LoginAttempt.success.is_(False))
    if q.filter(LoginAttempt.email == email).count() >= settings.MAX_FAILED_PER_EMAIL \
            or q.filter(LoginAttempt.ip == ip).count() >= settings.MAX_FAILED_PER_IP:
        raise HTTPException(429, f"Too many failed sign-ins. Try again in {settings.LOCKOUT_MINUTES} minutes.")


def record_attempt(db: Session, email: str, ip: str, success: bool):
    from ..db.models import LoginAttempt
    db.add(LoginAttempt(email=email, ip=ip, success=success, at=_now()))
    # keep the table small
    db.query(LoginAttempt).filter(LoginAttempt.at < _now() - timedelta(days=2)).delete()
