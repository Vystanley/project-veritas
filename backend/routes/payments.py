"""Stripe checkout, status, and webhook routes."""

import logging
import uuid
from datetime import datetime, timezone, timedelta

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request

from auth import get_current_user
from config import PLANS, STRIPE_API_KEY
from database import db
from models import CheckoutRequest

logger = logging.getLogger(__name__)
router = APIRouter()

# Configure the stripe SDK once at module level.
stripe.api_key = STRIPE_API_KEY


@router.post("/payments/checkout")
async def create_checkout(data: CheckoutRequest, request: Request, user=Depends(get_current_user)):
    if not STRIPE_API_KEY:
        raise HTTPException(status_code=503, detail="Payments are not configured on this server")
    if data.plan not in PLANS:
        raise HTTPException(status_code=400, detail="Invalid plan")
    plan = PLANS[data.plan]
    origin = data.origin_url.rstrip("/")

    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": plan["currency"],
                "unit_amount": int(float(plan["amount"]) * 100),  # Stripe uses cents
                "product_data": {"name": plan["label"]},
            },
            "quantity": 1,
        }],
        success_url=f"{origin}/payment-success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{origin}/home",
        metadata={"user_id": user["id"], "plan": data.plan},
    )

    await db.payment_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "session_id": session.id,
        "user_id": user["id"],
        "plan": data.plan,
        "amount": float(plan["amount"]),
        "currency": plan["currency"],
        "payment_status": "pending",
        "status": "initiated",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"url": session.url, "session_id": session.id}


@router.get("/payments/status/{session_id}")
async def get_payment_status(session_id: str, request: Request, user=Depends(get_current_user)):
    if not STRIPE_API_KEY:
        raise HTTPException(status_code=503, detail="Payments are not configured on this server")
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Could not check payment status")

    payment_status = session.payment_status  # "paid", "unpaid", "no_payment_required"

    tx = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if tx and tx.get("payment_status") != "paid" and payment_status == "paid":
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
        "status": session.status,
        "payment_status": payment_status,
        "amount_total": session.amount_total,
        "currency": session.currency,
    }


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
    # If you have a webhook signing secret, verify here. For now, parse the event directly.
    try:
        event = stripe.Event.construct_from(stripe.util.json.loads(body), stripe.api_key)
        if event.type == "checkout.session.completed":
            session = event.data.object
            if session.payment_status == "paid":
                tx = await db.payment_transactions.find_one({"session_id": session.id}, {"_id": 0})
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
                        {"session_id": session.id},
                        {"$set": {"payment_status": "paid", "status": "complete", "completed_at": now.isoformat()}},
                    )
    except Exception as e:
        logger.error(f"Webhook error: {e}")
    return {"received": True}
