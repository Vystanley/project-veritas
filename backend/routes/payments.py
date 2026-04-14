"""Stripe checkout, status, and webhook routes."""

import logging
import uuid
from datetime import datetime, timezone, timedelta

from emergentintegrations.payments.stripe.checkout import (
    CheckoutSessionRequest,
    StripeCheckout,
)
from fastapi import APIRouter, Depends, HTTPException, Request

from auth import get_current_user
from config import PLANS, STRIPE_API_KEY
from database import db
from models import CheckoutRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/payments/checkout")
async def create_checkout(data: CheckoutRequest, request: Request, user=Depends(get_current_user)):
    if data.plan not in PLANS:
        raise HTTPException(status_code=400, detail="Invalid plan")
    plan = PLANS[data.plan]
    origin = data.origin_url.rstrip("/")
    host_url = str(request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    session = await stripe_checkout.create_checkout_session(CheckoutSessionRequest(
        amount=float(plan["amount"]),
        currency=plan["currency"],
        success_url=f"{origin}/payment-success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{origin}/home",
        metadata={"user_id": user["id"], "plan": data.plan},
    ))
    await db.payment_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "session_id": session.session_id,
        "user_id": user["id"],
        "plan": data.plan,
        "amount": float(plan["amount"]),
        "currency": plan["currency"],
        "payment_status": "pending",
        "status": "initiated",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"url": session.url, "session_id": session.session_id}


@router.get("/payments/status/{session_id}")
async def get_payment_status(session_id: str, request: Request, user=Depends(get_current_user)):
    host_url = str(request.base_url).rstrip("/")
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=f"{host_url}/api/webhook/stripe")
    try:
        status = await stripe_checkout.get_checkout_status(session_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Could not check payment status")
    tx = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if tx and tx.get("payment_status") != "paid" and status.payment_status == "paid":
        plan_info = PLANS.get(tx["plan"], PLANS["premium_monthly"])
        now = datetime.now(timezone.utc)
        await db.subscriptions.update_one(
            {"user_id": user["id"]},
            {"$set": {
                "plan": tx["plan"],
                "started_at": now.isoformat(),
                "expires_at": (now + timedelta(days=plan_info["days"])).isoformat(),
            }},
            upsert=True,
        )
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {"payment_status": "paid", "status": "complete", "completed_at": now.isoformat()}},
        )
    return {
        "status": status.status,
        "payment_status": status.payment_status,
        "amount_total": status.amount_total,
        "currency": status.currency,
    }


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
    host_url = str(request.base_url).rstrip("/")
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=f"{host_url}/api/webhook/stripe")
    try:
        event = await stripe_checkout.handle_webhook(body, sig)
        if event.payment_status == "paid":
            tx = await db.payment_transactions.find_one({"session_id": event.session_id}, {"_id": 0})
            if tx and tx.get("payment_status") != "paid":
                plan_info = PLANS.get(tx["plan"], PLANS["premium_monthly"])
                now = datetime.now(timezone.utc)
                await db.subscriptions.update_one(
                    {"user_id": tx["user_id"]},
                    {"$set": {
                        "plan": tx["plan"],
                        "started_at": now.isoformat(),
                        "expires_at": (now + timedelta(days=plan_info["days"])).isoformat(),
                    }},
                    upsert=True,
                )
                await db.payment_transactions.update_one(
                    {"session_id": event.session_id},
                    {"$set": {"payment_status": "paid", "status": "complete", "completed_at": now.isoformat()}},
                )
    except Exception as e:
        logger.error(f"Webhook error: {e}")
    return {"received": True}
