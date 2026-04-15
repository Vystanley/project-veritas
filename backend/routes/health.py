"""Health check."""

from fastapi import APIRouter, Request

from rate_limit import limiter

router = APIRouter()


@router.get("/health")
@limiter.exempt
async def health(request: Request):
    """Exempt from rate limiting — Render's own health poller hits this frequently
    and we don't want platform pings to trip the global 120/hour default."""
    return {"status": "ok", "service": "veritas-api"}
