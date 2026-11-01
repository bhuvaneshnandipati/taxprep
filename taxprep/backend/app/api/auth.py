from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..db.models import User, AuditLog, TaxReturn, Document
from ..core.config import settings
from ..core.security import (COOKIE, hash_password, verify_password, create_session, end_session,
                             end_all_sessions, request_token, current_user_email, check_throttle,
                             record_attempt, client_ip)
import os, hmac
from ..schemas import RegisterIn, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_cookie(resp: Response, token: str):
    resp.set_cookie(COOKIE, token, httponly=True, secure=settings.PRODUCTION, samesite="strict",
                    max_age=settings.SESSION_MAX_HOURS * 3600, path="/")


def _signup_state(db: Session) -> dict:
    users = db.query(User).count()
    return {"open": settings.MAX_USERS > 0 and users < settings.MAX_USERS,
            "remaining": max(0, settings.MAX_USERS - users)}


@router.get("/signup-status")
def signup_status(db: Session = Depends(get_db)):
    """Lets the sign-in page say whether new accounts can still be created."""
    return {"open": _signup_state(db)["open"]}


@router.post("/register", response_model=TokenOut)
def register(body: RegisterIn, request: Request, response: Response, db: Session = Depends(get_db)):
    from datetime import datetime, timedelta, timezone
    email = body.email.lower()
    admins = [e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()]
    is_admin = email in admins
    if not is_admin:
        if settings.REGISTRATION_EMAILS and email not in settings.REGISTRATION_EMAILS:
            raise HTTPException(403, "Sign-up is limited to invited emails.")
        if not _signup_state(db)["open"]:
            raise HTTPException(403, "Sign-up is full: the maximum number of accounts has been reached.")
        ip = client_ip(request)
        since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
        recent = db.query(AuditLog).filter(AuditLog.action == "register", AuditLog.detail == ip,
                                           AuditLog.at >= since).count()
        if recent >= settings.MAX_SIGNUPS_PER_IP_PER_DAY:
            raise HTTPException(429, "Too many new accounts from this network today. Try again tomorrow.")
    if db.query(User).filter_by(email=email).first():
        raise HTTPException(400, "Email already registered")
    role = "user"
    if is_admin:
        code = os.getenv("ADMIN_SETUP_CODE", "")
        if not code or not hmac.compare_digest(code, body.admin_code or ""):
            raise HTTPException(403, "This email is reserved for the administrator. Enter the admin setup code.")
        role = "admin"
    u = User(email=email, hashed_password=hash_password(body.password), full_name=body.full_name, role=role)
    db.add(u); db.add(AuditLog(user_email=email, action="register", detail=client_ip(request)))
    token = create_session(db, email); db.commit()
    _set_cookie(response, token)
    return TokenOut(access_token=token)


@router.post("/login", response_model=TokenOut)
def login(request: Request, response: Response, form: OAuth2PasswordRequestForm = Depends(),
          db: Session = Depends(get_db)):
    email, ip = form.username.strip().lower(), client_ip(request)
    check_throttle(db, email, ip)
    u = db.query(User).filter_by(email=email).first()
    ok = bool(u) and verify_password(form.password, u.hashed_password)
    record_attempt(db, email, ip, ok)
    if not ok:
        db.commit()
        raise HTTPException(401, "Incorrect email or password")
    db.add(AuditLog(user_email=u.email, action="login"))
    token = create_session(db, u.email); db.commit()
    _set_cookie(response, token)
    return TokenOut(access_token=token)


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    end_session(db, request_token(request)); db.commit()
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@router.get("/me")
def me(email: str = Depends(current_user_email), db: Session = Depends(get_db)):
    u = db.query(User).filter_by(email=email).first()
    return {"email": email, "full_name": u.full_name if u else "", "role": u.role if u else ""}


@router.delete("/account")
def delete_account(response: Response, email: str = Depends(current_user_email), db: Session = Depends(get_db)):
    """Permanently delete the account, every return and every document. Cannot be undone."""
    u = db.query(User).filter_by(email=email).first()
    for r in db.query(TaxReturn).filter_by(user_id=u.id).all():
        db.query(Document).filter_by(return_id=r.id).delete()
        db.delete(r)
    end_all_sessions(db, email)
    db.delete(u)
    db.add(AuditLog(user_email=email, action="account_delete"))
    db.commit()
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}
