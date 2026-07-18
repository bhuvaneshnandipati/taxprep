from sqlalchemy import Column, Integer, String, ForeignKey, JSON, DateTime, func
from sqlalchemy.orm import relationship
from .session import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, default="")
    role = Column(String, default="user")            # user | admin
    created_at = Column(DateTime, server_default=func.now())
    returns = relationship("TaxReturn", back_populates="user")

class TaxReturn(Base):
    __tablename__ = "tax_returns"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    tax_year = Column(Integer, default=2025)
    status = Column(String, default="in_progress")   # in_progress | complete
    answers = Column(JSON, default=dict)             # interview answers
    profile = Column(JSON, default=dict)             # residency inputs
    income = Column(JSON, default=dict)              # w2s, 1099s, deductions
    result_federal = Column(JSON, default=dict)
    result_state = Column(JSON, default=dict)
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
    extracted = Column(JSON, default=dict)      # {fields, needs_review, ...}
    status = Column(String, default="extracted") # extracted | reviewed | applied
    uploaded_at = Column(DateTime, server_default=func.now())
