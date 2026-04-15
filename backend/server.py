"""Veritas API — FastAPI application entry point.

This module wires together configuration, middleware, exception handlers, and
feature routers. All business logic lives in the `services/` and `routes/`
packages; this file stays small on purpose.
"""

import logging
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.cors import CORSMiddleware

from database import client  # noqa: F401 — imported so the client connects at startup
from rate_limit import limiter
from routes import (
    account as account_routes,
    auth as auth_routes,
    fact_check as fact_check_routes,
    health as health_routes,
    notifications as notifications_routes,
    payments as payments_routes,
    referral as referral_routes,
    subscription as subscription_routes,
)
from fastapi import APIRouter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Veritas API", version="1.0.0")

# ---- Rate limiting ----
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ---- Exception handlers ----

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    messages = []
    for e in errors:
        field = e.get("loc", [])[-1] if e.get("loc") else "field"
        msg = e.get("msg", "Invalid value")
        if "email" in str(field).lower():
            messages.append("Please enter a valid email address")
        elif "password" in str(field).lower():
            messages.append(f"Invalid password: {msg}")
        else:
            messages.append(f"{field}: {msg}")
    detail = ". ".join(dict.fromkeys(messages))
    return JSONResponse(status_code=400, content={"detail": detail})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch ALL unhandled exceptions and return JSON — never raw text."""
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again.", "status": "error"},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Ensure HTTPExceptions also return clean JSON."""
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc.detail)})


# ---- Routers ----

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_routes.router)
api_router.include_router(subscription_routes.router)
api_router.include_router(payments_routes.router)
api_router.include_router(referral_routes.router)
api_router.include_router(notifications_routes.router)
api_router.include_router(fact_check_routes.router)
api_router.include_router(account_routes.router)
api_router.include_router(health_routes.router)

app.include_router(api_router)

# ---- Middleware ----

# CORS: read allowed origins from env. Falls back to "*" locally for dev.
# Note: when allow_origins=["*"], allow_credentials MUST be False per the CORS spec.
# Since we use bearer-token auth (no cookies), that's fine.
_cors_env = os.environ.get("CORS_ALLOW_ORIGINS", "*").strip()
_cors_origins = ["*"] if _cors_env == "*" else [o.strip() for o in _cors_env.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_credentials=False,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Lifecycle ----

@app.on_event("startup")
async def startup_event():
    """Create DB indexes (idempotent — safe to run every boot)."""
    from jobs import ensure_indexes
    await ensure_indexes()


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
