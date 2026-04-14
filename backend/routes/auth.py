"""Auth routes: register, login, email verification, /me."""

import logging
import random
import re
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException

from auth import create_token, get_current_user, hash_password, verify_password
from config import (
    ACCOUNT_REUSE_COOLDOWN_DAYS,
    EMAIL_MOCK_MODE,
    VERIFICATION_CODE_EXPIRY_MINUTES,
)
from database import db
from models import (
    AuthResponse,
    UserLogin,
    UserRegister,
    UserResponse,
    VerifyEmailRequest,
)
from services.referral import ensure_referral_code

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth")

VALID_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def generate_verification_code() -> str:
    return str(random.randint(100000, 999999))


@router.post("/register", response_model=AuthResponse)
async def register(data: UserRegister):
    if not data.consent_accepted:
        raise HTTPException(status_code=400, detail="You must accept the Terms & Conditions to create an account")
    if not VALID_EMAIL_RE.match(data.email):
        raise HTTPException(status_code=400, detail="Please enter a valid email address")
    deleted = await db.deleted_accounts.find_one({"email": data.email}, {"_id": 0})
    if deleted:
        deleted_at = datetime.fromisoformat(deleted["deleted_at"])
        days_since = (datetime.now(timezone.utc) - deleted_at).days
        if days_since < ACCOUNT_REUSE_COOLDOWN_DAYS:
            remaining = ACCOUNT_REUSE_COOLDOWN_DAYS - days_since
            raise HTTPException(
                status_code=400,
                detail=f"This email was recently used on a deleted account. You can re-register in {remaining} day(s).",
            )
    if await db.users.find_one({"email": data.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    user_id = str(uuid.uuid4())
    await db.users.insert_one({
        "id": user_id,
        "name": data.name,
        "email": data.email,
        "password_hash": hash_password(data.password),
        "email_verified": False,
        "consent_accepted": True,
        "consent_accepted_at": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await ensure_referral_code(user_id)
    code = generate_verification_code()
    await db.verification_codes.delete_many({"user_id": user_id})
    await db.verification_codes.insert_one({
        "user_id": user_id,
        "email": data.email,
        "code": code,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (
            datetime.now(timezone.utc) + timedelta(minutes=VERIFICATION_CODE_EXPIRY_MINUTES)
        ).isoformat(),
    })
    logger.info(f"Verification code for {data.email}: {code} (mock mode: {EMAIL_MOCK_MODE})")
    return AuthResponse(
        token=create_token(user_id),
        user=UserResponse(id=user_id, name=data.name, email=data.email, email_verified=False),
        verification_code=code if EMAIL_MOCK_MODE else None,
    )


@router.post("/verify-email")
async def verify_email(data: VerifyEmailRequest, user=Depends(get_current_user)):
    record = await db.verification_codes.find_one({"user_id": user["id"]}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=400, detail="No verification code found. Please request a new one.")
    expires = datetime.fromisoformat(record["expires_at"])
    if datetime.now(timezone.utc) > expires:
        raise HTTPException(status_code=400, detail="Verification code has expired. Please request a new one.")
    if record["code"] != data.code:
        raise HTTPException(status_code=400, detail="Invalid verification code. Please try again.")
    await db.users.update_one({"id": user["id"]}, {"$set": {"email_verified": True}})
    await db.verification_codes.delete_many({"user_id": user["id"]})
    return {"success": True, "message": "Email verified successfully!"}


@router.post("/resend-code")
async def resend_verification_code(user=Depends(get_current_user)):
    u = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    if u and u.get("email_verified"):
        raise HTTPException(status_code=400, detail="Email is already verified")
    code = generate_verification_code()
    await db.verification_codes.delete_many({"user_id": user["id"]})
    await db.verification_codes.insert_one({
        "user_id": user["id"],
        "email": user["email"],
        "code": code,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (
            datetime.now(timezone.utc) + timedelta(minutes=VERIFICATION_CODE_EXPIRY_MINUTES)
        ).isoformat(),
    })
    logger.info(f"Resent verification code for {user['email']}: {code}")
    mock_code = code if EMAIL_MOCK_MODE else None
    return {"success": True, "message": "Verification code sent!", "verification_code": mock_code}


@router.post("/login")
async def login(data: UserLogin):
    user = await db.users.find_one({"email": data.email}, {"_id": 0})
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    verified = user.get("email_verified", False)

    base_response = {
        "token": create_token(user["id"]),
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "email_verified": verified,
        },
    }

    if not verified:
        code = generate_verification_code()
        await db.verification_codes.delete_many({"user_id": user["id"]})
        await db.verification_codes.insert_one({
            "user_id": user["id"],
            "email": user["email"],
            "code": code,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (
                datetime.now(timezone.utc) + timedelta(minutes=VERIFICATION_CODE_EXPIRY_MINUTES)
            ).isoformat(),
        })
        if EMAIL_MOCK_MODE:
            base_response["verification_code"] = code

    return base_response


@router.get("/me", response_model=UserResponse)
async def get_me(user=Depends(get_current_user)):
    u = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    verified = u.get("email_verified", False) if u else False
    return UserResponse(id=user["id"], name=user["name"], email=user["email"], email_verified=verified)
