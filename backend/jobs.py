"""Fact-check job storage, backed by MongoDB so jobs survive backend restarts.

Usage:
    job = FactCheckJob(job_id, video_url, user_id)
    await job.save()                 # persist the new job

    # ...later, mutate attributes as usual and re-persist:
    job.status = "processing"
    job.progress = 20
    await job.save()

    # From a different coroutine (e.g. the /status endpoint):
    job = await get_job(job_id)      # reads from Mongo
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from database import db

logger = logging.getLogger(__name__)

_jobs = db["fact_check_jobs"]

# How long a completed/failed job stays in the DB so the client can poll for its result.
JOB_TTL_HOURS = 1


class FactCheckJob:
    """Represents a fact-check job. Attributes mirror the old in-memory class so existing
    code that mutates ``job.status``, ``job.progress``, etc. keeps working. Call
    ``await job.save()`` to persist changes to Mongo.
    """

    __slots__ = (
        "job_id", "video_url", "user_id",
        "status", "progress", "progress_message",
        "result", "error", "created_at",
    )

    def __init__(self, job_id: str, video_url: str, user_id: str):
        self.job_id = job_id
        self.video_url = video_url
        self.user_id = user_id
        self.status = "pending"  # pending → processing → completed / failed
        self.progress = 0
        self.progress_message = "Queued for processing..."
        self.result: Optional[dict] = None
        self.error: Optional[str] = None
        self.created_at = datetime.now(timezone.utc)

    def to_doc(self) -> dict[str, Any]:
        """Serialize this job to a Mongo document."""
        return {
            "_id": self.job_id,
            "job_id": self.job_id,
            "video_url": self.video_url,
            "user_id": self.user_id,
            "status": self.status,
            "progress": self.progress,
            "progress_message": self.progress_message,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": datetime.now(timezone.utc),
        }

    @classmethod
    def from_doc(cls, doc: dict[str, Any]) -> "FactCheckJob":
        job = cls.__new__(cls)
        job.job_id = doc.get("job_id") or doc.get("_id")
        job.video_url = doc.get("video_url", "")
        job.user_id = doc.get("user_id", "")
        job.status = doc.get("status", "pending")
        job.progress = doc.get("progress", 0)
        job.progress_message = doc.get("progress_message", "")
        job.result = doc.get("result")
        job.error = doc.get("error")
        created = doc.get("created_at")
        job.created_at = created if isinstance(created, datetime) else datetime.now(timezone.utc)
        return job

    async def save(self) -> None:
        """Persist (upsert) the current state to Mongo."""
        try:
            await _jobs.update_one(
                {"_id": self.job_id},
                {"$set": self.to_doc()},
                upsert=True,
            )
        except Exception as e:
            # We deliberately log-and-continue: a persistence failure shouldn't kill the pipeline
            # mid-scan. The user will still get a result via the in-memory object reference the
            # background task is holding.
            logger.warning(f"Job persist failed for {self.job_id}: {e}")


async def create_job(job_id: str, video_url: str, user_id: str) -> FactCheckJob:
    """Create a new job and persist its initial state."""
    job = FactCheckJob(job_id, video_url, user_id)
    await job.save()
    return job


async def get_job(job_id: str) -> Optional[FactCheckJob]:
    """Fetch a job from Mongo by ID, or return None if not found / expired."""
    try:
        doc = await _jobs.find_one({"_id": job_id})
        if not doc:
            return None
        return FactCheckJob.from_doc(doc)
    except Exception as e:
        logger.warning(f"Job fetch failed for {job_id}: {e}")
        return None


async def cleanup_old_jobs() -> int:
    """Delete jobs older than JOB_TTL_HOURS. Returns the number of jobs deleted."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=JOB_TTL_HOURS)
    try:
        result = await _jobs.delete_many({"created_at": {"$lt": cutoff}})
        return result.deleted_count or 0
    except Exception as e:
        logger.warning(f"Job cleanup failed: {e}")
        return 0


async def ensure_indexes() -> None:
    """Create indexes for efficient lookups and automatic TTL-based cleanup."""
    try:
        # TTL index: Mongo auto-deletes jobs older than JOB_TTL_HOURS.
        # expireAfterSeconds is relative to the value of `created_at`.
        await _jobs.create_index(
            "created_at",
            expireAfterSeconds=JOB_TTL_HOURS * 3600,
            name="jobs_ttl",
        )
        await _jobs.create_index("user_id", name="jobs_user_id")
    except Exception as e:
        logger.warning(f"Could not create job indexes: {e}")
