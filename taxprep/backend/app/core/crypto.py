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


# ---------------------------------------------------------------- whole-column encryption
# Return data (names, addresses, income, results, OCR output) is encrypted as a whole
# with the same DATA_KEY. Stored shape: {"_enc": "<fernet token>"} inside the existing
# JSON column, so no schema migration is needed and legacy plaintext rows still load
# (they are re-encrypted on their next save).
import json as _json
from sqlalchemy.types import TypeDecorator, JSON as _JSON, String as _String


class EncryptedJSON(TypeDecorator):
    impl = _JSON
    cache_ok = True

    def process_bind_param(self, value, dialect):
        f = _fernet()
        if value is None or not f:
            return value
        return {"_enc": f.encrypt(_json.dumps(value, separators=(",", ":")).encode()).decode()}

    def process_result_value(self, value, dialect):
        if isinstance(value, dict) and set(value) == {"_enc"}:
            f = _fernet()
            if not f:
                raise RuntimeError("Encrypted data found but DATA_KEY is not set")
            return _json.loads(f.decrypt(value["_enc"].encode()))
        return value


class EncryptedString(TypeDecorator):
    impl = _String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return enc(value) if value else value

    def process_result_value(self, value, dialect):
        return dec(value) if value else value


def mask_id(v: str) -> str:
    """SSN/ITIN shown back to the browser: only the last four digits."""
    d = "".join(ch for ch in str(v or "") if ch.isdigit())
    return f"***-**-{d[-4:]}" if len(d) >= 4 else ""


def is_masked(v) -> bool:
    return isinstance(v, str) and v.startswith("***-**-")
