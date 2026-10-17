from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
import bcrypt
import hashlib
import base64
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from .config import settings

oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")

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

def create_token(sub: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_MINUTES)
    return jwt.encode({"sub": sub, "exp": exp}, settings.JWT_SECRET, algorithm=settings.JWT_ALG)

def current_user_email(token: str = Depends(oauth2)) -> str:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
        return payload["sub"]
    except (JWTError, KeyError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
