"""Field-level encryption for identifiers stored in the database (SSN/ITIN, passport number).

Set DATA_KEY to a Fernet key (python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())").
Without DATA_KEY values are stored as entered (fine for local development only).
Encrypted values are prefixed with 'enc:' so old plaintext rows keep working after the key is added.
"""
import os
from functools import lru_cache

SENSITIVE = ("ssn", "passport_number")


@lru_cache(maxsize=1)
def _fernet():
    key = os.getenv("DATA_KEY", "").strip()
    if not key:
        return None
    from cryptography.fernet import Fernet
    return Fernet(key.encode())


def enc(v: str) -> str:
    f = _fernet()
    if not v or not f or str(v).startswith("enc:"):
        return v
    return "enc:" + f.encrypt(str(v).encode()).decode()


def dec(v: str) -> str:
    if not v or not str(v).startswith("enc:"):
        return v
    f = _fernet()
    if not f:
        return ""          # encrypted but no key configured: never leak ciphertext into forms
    return f.decrypt(str(v)[4:].encode()).decode()


def protect(d: dict) -> dict:
    return {k: (enc(v) if k in SENSITIVE else v) for k, v in (d or {}).items()}


def reveal(d: dict) -> dict:
    return {k: (dec(v) if k in SENSITIVE else v) for k, v in (d or {}).items()}
