"""Account deletion (GDPR) route."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from auth import get_current_user
from database import db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/account")


@router.delete("/delete")
async def delete_account(user=Depends(get_current_user)):
    uid = user["id"]
    email = user.get("email", "")
    if email:
        await db.deleted_accounts.update_one(
            {"email": email},
            {"$set": {
                "email": email,
                "deleted_at": datetime.now(timezone.utc).isoformat(),
                "user_id": uid,
            }},
            upsert=True,
        )
    for col in ["users", "subscriptions", "scan_logs", "payment_transactions", "referrals", "push_tokens"]:
        await db[col].delete_many({"user_id": uid} if col != "users" else {"id": uid})
    await db.referral_log.delete_many(
        {"$or": [{"referrer_user_id": uid}, {"referred_user_id": uid}]}
    )
    logger.info(f"Deleted all data for user {uid}")
    return {"success": True, "message": "All your data has been permanently deleted."}
