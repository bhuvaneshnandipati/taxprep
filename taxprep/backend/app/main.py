from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db.session import Base, engine
from .api import auth, returns, interview, documents, admin

Base.metadata.create_all(bind=engine)

app = FastAPI(title="TaxPrep API", version="0.1.0",
              description="Tax return preparation API — federal (1040/1040-NR) + California, TY-versioned rules engine.")
from .core.config import settings
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Content-Type", "Authorization", "X-TaxPrep"])
app.include_router(auth.router)
app.include_router(returns.router)
app.include_router(interview.router)
app.include_router(documents.router)
app.include_router(admin.router)

from fastapi.responses import JSONResponse
from .core.security import COOKIE

@app.middleware("http")
async def private_responses(request, call_next):
    # CSRF guard: a browser using the session cookie must send the X-TaxPrep header on
    # every state-changing request. Other sites cannot add custom headers without CORS,
    # which only allows our own origin.
    if request.method not in ("GET", "HEAD", "OPTIONS") and COOKIE in request.cookies \
            and not request.headers.get("authorization") and request.headers.get("x-taxprep") != "1":
        return JSONResponse({"detail": "Missing X-TaxPrep header"}, status_code=403)
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response

@app.get("/health")
def health():
    return {"status": "ok"}
