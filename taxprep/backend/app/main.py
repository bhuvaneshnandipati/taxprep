from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db.session import Base, engine
from .api import auth, returns, interview, documents, admin

Base.metadata.create_all(bind=engine)

app = FastAPI(title="TaxPrep API", version="0.1.0",
              description="Tax return preparation API — federal (1040/1040-NR) + California, TY-versioned rules engine.")
from .core.config import settings
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth.router)
app.include_router(returns.router)
app.include_router(interview.router)
app.include_router(documents.router)
app.include_router(admin.router)

@app.get("/health")
def health():
    return {"status": "ok"}
