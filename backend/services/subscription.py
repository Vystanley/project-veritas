"""Subscription state, scan counting, and rate-limit checks."""

from datetime import datetime, timezone, timedelta

from fastapi import HTTPException

from config import FREE_SCANS_PER_WEEK, PREMIUM_FUP_MONTHLY_CAP
from database import db


def get_week_start() -> datetime:
    now = datetime.now(timezone.utc)
    return (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)


def get_month_start() -> datetime:
    return datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def get_subscription(user_id: str) -> dict:
    sub = await db.subscriptions.find_one({"user_id": user_id}, {"_id": 0})
    if not sub:
        sub = {
            "user_id": user_id,
            "plan": "free",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": None,
            "bonus_scans": 0,
        }
        await db.subscriptions.insert_one(sub)
        sub.pop("_id", None)
    else:
        defaults = {
            "plan": "free",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": None,
            "bonus_scans": 0,
        }
        needs_update = {k: v for k, v in defaults.items() if k not in sub}
        if needs_update:
            sub.update(needs_update)
            await db.subscriptions.update_one({"user_id": user_id}, {"$set": needs_update})
    return sub


async def count_scans_this_week(user_id: str) -> int:
    return await db.scan_logs.count_documents(
        {"user_id": user_id, "created_at": {"$gte": get_week_start().isoformat()}}
    )


async def count_scans_this_month(user_id: str) -> int:
    return await db.scan_logs.count_documents(
        {"user_id": user_id, "created_at": {"$gte": get_month_start().isoformat()}}
    )


async def check_scan_limit(user_id: str):
    sub = await get_subscription(user_id)
    is_premium = sub["plan"] in ("premium_monthly", "premium_annual")
    if is_premium and sub.get("expires_at"):
        if datetime.now(timezone.utc) > datetime.fromisoformat(sub["expires_at"]):
            await db.subscriptions.update_one(
                {"user_id": user_id}, {"$set": {"plan": "free", "expires_at": None}}
            )
            is_premium = False
    if is_premium:
        if await count_scans_this_month(user_id) >= PREMIUM_FUP_MONTHLY_CAP:
            raise HTTPException(status_code=429, detail="Monthly scan limit reached. Resets next month.")
    else:
        bonus = sub.get("bonus_scans", 0)
        if await count_scans_this_week(user_id) >= FREE_SCANS_PER_WEEK + bonus:
            raise HTTPException(
                status_code=429,
                detail="You've used all free scans this week. Upgrade to Premium for unlimited scans!",
            )


async def log_scan(user_id: str, video_url: str, check_id: str):
    await db.scan_logs.insert_one({
        "user_id": user_id,
        "video_url": video_url,
        "check_id": check_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
