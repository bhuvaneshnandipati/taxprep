from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from ..core.config import settings

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")
_connect_args = ({"check_same_thread": False} if _is_sqlite
                 else {} if "sslmode" in settings.DATABASE_URL
                 else {"sslmode": settings.DB_SSLMODE})
engine = create_engine(settings.DATABASE_URL, connect_args=_connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
