import os

def _normalize_db_url(url: str) -> str:
    # Neon/Render/Railway/Supabase often hand out "postgres://"; SQLAlchemy 2.x requires "postgresql://"
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url

class Settings:
    APP_NAME = "TaxPrep API"
    DATABASE_URL = _normalize_db_url(os.getenv("DATABASE_URL", "sqlite:///./taxprep.db"))
    JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-prod")
    JWT_ALG = "HS256"
    ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "240"))
    DEFAULT_TAX_YEAR = 2025
    # "require" is correct for managed Postgres (Neon/Render/Supabase). Set
    # DB_SSLMODE=disable for a self-hosted Postgres (e.g. reached via an ngrok
    # tunnel) that has no SSL certificate configured.
    DB_SSLMODE = os.getenv("DB_SSLMODE", "require")
    # Exact website origins; local development is restricted to its frontend.
    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")]

settings = Settings()

def validate_production_settings():
    production = any(os.getenv(name, "").lower() not in ("", "0", "false")
                     for name in ("PRODUCTION", "RENDER", "VERCEL"))
    if not production:
        return
    if len(settings.JWT_SECRET) < 32 or settings.JWT_SECRET in {"dev-secret-change-in-prod", "change-me"}:
        raise RuntimeError("JWT_SECRET must contain at least 32 random characters in production")
    from cryptography.fernet import Fernet
    try:
        Fernet(os.environ.get("DATA_KEY", "").encode())
    except (ValueError, TypeError):
        raise RuntimeError("A valid persistent DATA_KEY is required in production") from None
    if not settings.DATABASE_URL.startswith("postgresql://"):
        raise RuntimeError("A persistent PostgreSQL DATABASE_URL is required in production")
    if not settings.CORS_ORIGINS or any(not o.startswith("https://") or "*" in o for o in settings.CORS_ORIGINS):
        raise RuntimeError("CORS_ORIGINS must list explicit HTTPS website origins in production")


validate_production_settings()
