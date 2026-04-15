"""Fact-check job submission and status polling."""

import hashlib
import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from slowapi.util import get_remote_address

from auth import get_current_user
from jobs import cleanup_old_jobs, create_job, get_job
from models import FactCheckRequest
from rate_limit import limiter
from services.fact_check import process_fact_check_background
from services.subscription import check_scan_limit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/fact-check")


DEMO_USER_PREFIX = "demo-"


def _demo_user_id(request: Request) -> str:
    """Derive a stable synthetic user id from the caller's IP.

    Lets us scope demo jobs per-visitor (so one visitor can poll their own
    jobs) without storing any real PII.
    """
    ip = get_remote_address(request) or "unknown"
    h = hashlib.sha256(ip.encode("utf-8")).hexdigest()[:16]
    return f"{DEMO_USER_PREFIX}{h}"


@router.post("")
async def fact_check(
    data: FactCheckRequest,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
):
    """Submit a fact-check job. Returns a job_id immediately; process runs in background."""
    logger.info(f"Fact-check requested for URL: {data.video_url}")
    await check_scan_limit(user["id"])

    await cleanup_old_jobs()
    job_id = str(uuid.uuid4())
    job = await create_job(job_id, data.video_url, user["id"])

    background_tasks.add_task(process_fact_check_background, job)

    return JSONResponse(status_code=202, content={
        "job_id": job_id,
        "status": "pending",
        "message": "Analysis started",
    })


@router.get("/{job_id}/status")
async def fact_check_status(job_id: str, user=Depends(get_current_user)):
    """Poll for fact-check job progress and results."""
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or expired")
    if job.user_id != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to view this job")

    response = {
        "job_id": job.job_id,
        "status": job.status,
        "progress": job.progress,
        "progress_message": job.progress_message,
    }
    if job.status == "completed" and job.result:
        response["result"] = job.result
    if job.status == "failed" and job.error:
        response["error"] = job.error

    return response


# ----------------------------------------------------------------------------
# Public demo endpoints — no auth required, strict per-IP rate limits.
# These power the web demo at veritas.example.com so random visitors can try
# the product without creating an account.
# ----------------------------------------------------------------------------

@router.post("/demo")
@limiter.limit("3/day")
async def fact_check_demo(
    data: FactCheckRequest,
    background_tasks: BackgroundTasks,
    request: Request,
):
    """Anonymous fact-check. Rate-limited to 3 per IP per day."""
    logger.info(f"Demo fact-check requested for URL: {data.video_url}")
    await cleanup_old_jobs()
    job_id = str(uuid.uuid4())
    demo_uid = _demo_user_id(request)
    job = await create_job(job_id, data.video_url, demo_uid)
    background_tasks.add_task(process_fact_check_background, job)
    return JSONResponse(status_code=202, content={
        "job_id": job_id,
        "status": "pending",
        "message": "Analysis started",
    })


@router.get("/demo/{job_id}/status")
@limiter.limit("120/minute")   # polling is frequent; this is per-IP
async def fact_check_demo_status(job_id: str, request: Request):
    """Public status polling for demo jobs only."""
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or expired")
    if not job.user_id.startswith(DEMO_USER_PREFIX):
        # Don't leak authenticated jobs through the public endpoint.
        raise HTTPException(status_code=403, detail="Not a demo job")

    response = {
        "job_id": job.job_id,
        "status": job.status,
        "progress": job.progress,
        "progress_message": job.progress_message,
    }
    if job.status == "completed" and job.result:
        response["result"] = job.result
    if job.status == "failed" and job.error:
        response["error"] = job.error
    return response
