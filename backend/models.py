"""Pydantic request/response models."""

from typing import List, Optional

from pydantic import BaseModel, EmailStr


class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    consent_accepted: bool = False


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    email_verified: bool = False


class AuthResponse(BaseModel):
    token: str
    user: UserResponse
    verification_code: Optional[str] = None  # Only in mock mode


class VerifyEmailRequest(BaseModel):
    code: str


class ResendCodeRequest(BaseModel):
    email: str


class FactCheckRequest(BaseModel):
    video_url: str


class ClaimResult(BaseModel):
    claim: str
    verdict: str
    explanation: str
    sources: List[str] = []


class DeepfakeResult(BaseModel):
    is_deepfake: bool
    confidence: int
    risk_level: str  # "low", "medium", "high"
    analysis: str
    indicators: List[str] = []


class ReverseImageResult(BaseModel):
    enabled: bool = False
    frame_url: Optional[str] = None
    matches: List[dict] = []
    earliest_date: Optional[str] = None
    note: str = ""


class FactCheckResponse(BaseModel):
    id: str
    overall_verdict: str
    confidence_score: int
    summary: str
    transcript: str
    visual_description: Optional[str] = None
    claims: List[ClaimResult]
    sources: List[dict] = []
    deepfake: DeepfakeResult
    reverse_image: Optional[ReverseImageResult] = None
    video_url: str
    created_at: str


class SubscriptionStatus(BaseModel):
    plan: str
    scans_used: int
    scans_remaining: int
    is_premium: bool
    expires_at: Optional[str] = None
    period_resets_at: str
    bonus_scans: int = 0


class CheckoutRequest(BaseModel):
    plan: str
    origin_url: str


class ReferralApplyRequest(BaseModel):
    referral_code: str


class PushTokenRequest(BaseModel):
    push_token: str
