"""Referral code generation and lookup."""

import random
import string
from datetime import datetime, timezone

from database import db


def generate_referral_code(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


async def ensure_referral_code(user_id: str) -> str:
    ref = await db.referrals.find_one({"user_id": user_id}, {"_id": 0})
    if ref:
        return ref["code"]
    code = generate_referral_code()
    for _ in range(10):
        code = generate_referral_code()
        if not await db.referrals.find_one({"code": code}):
            break
    await db.referrals.insert_one({
        "user_id": user_id,
        "code": code,
        "referred_users": [],
        "bonus_scans_earned": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return code
