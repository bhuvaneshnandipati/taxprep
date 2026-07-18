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
    ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "30"))
    DEFAULT_TAX_YEAR = 2025
    # "require" is correct for managed Postgres (Neon/Render/Supabase). Set
    # DB_SSLMODE=disable for a self-hosted Postgres (e.g. reached via an ngrok
    # tunnel) that has no SSL certificate configured.
    DB_SSLMODE = os.getenv("DB_SSLMODE", "require")
    # comma-separated list; "*" (default) allows any origin — fine since auth uses
    # Bearer tokens, not cookies, so there's no CSRF surface from a permissive CORS policy
    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]

settings = Settings()
