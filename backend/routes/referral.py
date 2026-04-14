"""Referral info and code-apply routes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user
from config import REFERRAL_BONUS_SCANS
from database import db
from models import ReferralApplyRequest
from services.referral import ensure_referral_code
from services.subscription import get_subscription

router = APIRouter(prefix="/referral")


@router.get("/info")
async def referral_info(user=Depends(get_current_user)):
    code = await ensure_referral_code(user["id"])
    ref = await db.referrals.find_one({"user_id": user["id"]}, {"_id": 0})
    return {
        "code": code,
        "referred_count": len(ref.get("referred_users", [])),
        "bonus_scans_earned": ref.get("bonus_scans_earned", 0),
    }


@router.post("/apply")
async def apply_referral(data: ReferralApplyRequest, user=Depends(get_current_user)):
    code = data.referral_code.strip().upper()
    ref = await db.referrals.find_one({"code": code}, {"_id": 0})
    if not ref:
        raise HTTPException(status_code=404, detail="Invalid referral code")
    if ref["user_id"] == user["id"]:
        raise HTTPException(status_code=400, detail="You cannot use your own referral code")
    if await db.referral_log.find_one({"referred_user_id": user["id"]}):
        raise HTTPException(status_code=400, detail="You have already used a referral code")
    await get_subscription(ref["user_id"])
    await get_subscription(user["id"])
    await db.referrals.update_one(
        {"code": code},
        {"$push": {"referred_users": user["id"]}, "$inc": {"bonus_scans_earned": REFERRAL_BONUS_SCANS}},
    )
    await db.subscriptions.update_one(
        {"user_id": ref["user_id"]}, {"$inc": {"bonus_scans": REFERRAL_BONUS_SCANS}}
    )
    await db.subscriptions.update_one(
        {"user_id": user["id"]}, {"$inc": {"bonus_scans": REFERRAL_BONUS_SCANS}}
    )
    await db.referral_log.insert_one({
        "referrer_user_id": ref["user_id"],
        "referred_user_id": user["id"],
        "code": code,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {
        "success": True,
        "bonus_scans": REFERRAL_BONUS_SCANS,
        "message": f"You and your friend each received {REFERRAL_BONUS_SCANS} bonus scans!",
    }
