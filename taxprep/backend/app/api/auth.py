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


def _registration_allowed(email: str, admins: list[str]) -> bool:
    if email in admins:
        return True                     # still needs ADMIN_SETUP_CODE below
    if settings.REGISTRATION_EMAILS:
        return email in settings.REGISTRATION_EMAILS
    return not settings.PRODUCTION      # open only for local development


@router.post("/register", response_model=TokenOut)
def register(body: RegisterIn, response: Response, db: Session = Depends(get_db)):
    email = body.email.lower()
    admins = [e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()]
    if not _registration_allowed(email, admins):
        raise HTTPException(403, "Sign-up is by invitation only. Ask the site owner to add your email.")
    if db.query(User).filter_by(email=email).first():
        raise HTTPException(400, "Email already registered")
    role = "user"
    if email in admins:
        code = os.getenv("ADMIN_SETUP_CODE", "")
        if not code or not hmac.compare_digest(code, body.admin_code or ""):
            raise HTTPException(403, "This email is reserved for the administrator. Enter the admin setup code.")
        role = "admin"
    u = User(email=email, hashed_password=hash_password(body.password), full_name=body.full_name, role=role)
    db.add(u); db.add(AuditLog(user_email=email, action="register"))
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
