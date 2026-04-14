"""Push notification registration and schedule endpoints."""

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends

from auth import get_current_user
from database import db
from models import PushTokenRequest
from services.subscription import get_week_start

router = APIRouter(prefix="/notifications")


@router.post("/register")
async def register_push_token(data: PushTokenRequest, user=Depends(get_current_user)):
    await db.push_tokens.update_one(
        {"user_id": user["id"]},
        {"$set": {"push_token": data.push_token, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"success": True}


@router.get("/schedule")
async def get_notification_schedule(user=Depends(get_current_user)):
    next_reset = get_week_start() + timedelta(days=7)
    return {"next_reset": next_reset.isoformat(), "next_reset_day": next_reset.strftime("%A, %B %d")}
