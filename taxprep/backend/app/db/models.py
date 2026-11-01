from sqlalchemy import Column, Integer, String, ForeignKey, JSON, DateTime, Boolean, func
from ..core.crypto import EncryptedJSON, EncryptedString
from sqlalchemy.orm import relationship
from .session import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(EncryptedString, default="")
    role = Column(String, default="user")            # user | admin
    created_at = Column(DateTime, server_default=func.now())
    returns = relationship("TaxReturn", back_populates="user")

class TaxReturn(Base):
    __tablename__ = "tax_returns"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    tax_year = Column(Integer, default=2025)
    status = Column(String, default="in_progress")   # in_progress | complete
    answers = Column(EncryptedJSON, default=dict)             # interview answers
    profile = Column(EncryptedJSON, default=dict)             # residency inputs
    income = Column(EncryptedJSON, default=dict)              # w2s, 1099s, deductions
    result_federal = Column(EncryptedJSON, default=dict)
    result_state = Column(EncryptedJSON, default=dict)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    user = relationship("User", back_populates="returns")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    user_email = Column(String, index=True)
    action = Column(String)
    detail = Column(String, default="")
    at = Column(DateTime, server_default=func.now())

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    return_id = Column(Integer, ForeignKey("tax_returns.id"), index=True)
    filename = Column(String)
    doc_type = Column(String, default="unknown")
    extracted = Column(EncryptedJSON, default=dict)      # {fields, needs_review, ...}
    status = Column(String, default="extracted") # extracted | reviewed | applied
    uploaded_at = Column(DateTime, server_default=func.now())


class AuthSession(Base):
    """Server-side login session. Only a SHA-256 hash of the token is stored, so a
    database leak does not expose usable session tokens. Deleting the row signs out."""
    __tablename__ = "auth_sessions"
    id = Column(Integer, primary_key=True)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)
    user_email = Column(String, index=True, nullable=False)
    created_at = Column(DateTime, nullable=False)
    last_seen = Column(DateTime, nullable=False)


class LoginAttempt(Base):
    """Recent sign-in attempts, used to lock out password guessing (works on serverless)."""
    __tablename__ = "login_attempts"
    id = Column(Integer, primary_key=True)
    email = Column(String, index=True)
    ip = Column(String, index=True)
    success = Column(Boolean, default=False)
    at = Column(DateTime, index=True, nullable=False)
