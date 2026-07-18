from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..db.models import User, AuditLog
from ..core.security import hash_password, verify_password, create_token
from ..schemas import RegisterIn, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=TokenOut)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter_by(email=body.email).first():
        raise HTTPException(400, "Email already registered")
    u = User(email=body.email, hashed_password=hash_password(body.password), full_name=body.full_name)
    db.add(u); db.add(AuditLog(user_email=body.email, action="register")); db.commit()
    return TokenOut(access_token=create_token(u.email))

@router.post("/login", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    u = db.query(User).filter_by(email=form.username).first()
    if not u or not verify_password(form.password, u.hashed_password):
        raise HTTPException(401, "Incorrect email or password")
    db.add(AuditLog(user_email=u.email, action="login")); db.commit()
    return TokenOut(access_token=create_token(u.email))
