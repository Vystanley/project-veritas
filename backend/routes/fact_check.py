"""Fact-check job submission and status polling."""

import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import JSONResponse

from auth import get_current_user
from jobs import cleanup_old_jobs, create_job, get_job
from models import FactCheckRequest
from services.fact_check import process_fact_check_background
from services.subscription import check_scan_limit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/fact-check")


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
