"""Subscription status & cancellation routes."""

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends

from auth import get_current_user
from config import FREE_SCANS_PER_WEEK, PREMIUM_FUP_MONTHLY_CAP
from database import db
from models import SubscriptionStatus
from services.subscription import (
    count_scans_this_month,
    count_scans_this_week,
    get_month_start,
    get_subscription,
    get_week_start,
)

router = APIRouter(prefix="/subscription")


@router.get("/status", response_model=SubscriptionStatus)
async def subscription_status(user=Depends(get_current_user)):
    sub = await get_subscription(user["id"])
    is_premium = sub["plan"] in ("premium_monthly", "premium_annual")
    if is_premium and sub.get("expires_at"):
        if datetime.now(timezone.utc) > datetime.fromisoformat(sub["expires_at"]):
            await db.subscriptions.update_one(
                {"user_id": user["id"]}, {"$set": {"plan": "free", "expires_at": None}}
            )
            is_premium = False
            sub["plan"] = "free"
    bonus = sub.get("bonus_scans", 0)
    if is_premium:
        scans_used = await count_scans_this_month(user["id"])
        scans_remaining = max(0, PREMIUM_FUP_MONTHLY_CAP - scans_used)
        next_period = (get_month_start().replace(day=28) + timedelta(days=4)).replace(day=1)
    else:
        scans_used = await count_scans_this_week(user["id"])
        scans_remaining = max(0, FREE_SCANS_PER_WEEK + bonus - scans_used)
        next_period = get_week_start() + timedelta(days=7)
    return SubscriptionStatus(
        plan=sub["plan"],
        scans_used=scans_used,
        scans_remaining=scans_remaining,
        is_premium=is_premium,
        expires_at=sub.get("expires_at"),
        period_resets_at=next_period.isoformat(),
        bonus_scans=bonus,
    )


@router.post("/cancel")
async def cancel_subscription(user=Depends(get_current_user)):
    await db.subscriptions.update_one(
        {"user_id": user["id"]}, {"$set": {"plan": "free", "expires_at": None}}
    )
    return {"success": True, "plan": "free"}
