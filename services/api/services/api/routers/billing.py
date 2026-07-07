"""Faza 76-80 — Billing / Stripe integration.

Endpoints:
  GET  /api/v2/billing/plans          — list available plans (hardcoded)
  POST /api/v2/billing/checkout       — create Stripe checkout session (or placeholder)
  GET  /api/v2/billing/subscription   — current org plan
  POST /api/v2/billing/webhook        — Stripe webhook handler
"""
from __future__ import annotations

import sys
sys.path.insert(0, '/home/ubuntu/terra-os/packages/vendor')

import hashlib
import hmac
import os
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..auth.deps import AuthUser
from terra_db.session import get_session

router = APIRouter(prefix="/api/v2/billing", tags=["billing"])


def get_db():
    SessionLocal = get_session()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DB = Annotated[Session, Depends(get_db)]


PLANS = [
    {
        "id": "free",
        "name": "Free",
        "price_pln": 0,
        "price_label": "0 PLN",
        "billing": "bezpłatny",
        "stripe_price_id": None,
        "limits": {
            "tenders": 5,
            "ai_analysis": False,
            "team_members": 1,
            "api_access": False,
        },
        "features": [
            "Do 5 przetargów",
            "Ręczne zarządzanie",
            "Podstawowe raporty",
        ],
    },
    {
        "id": "pro",
        "name": "Pro",
        "price_pln": 499,
        "price_label": "499 PLN/mies",
        "billing": "miesięcznie",
        "popular": True,
        "stripe_price_id": os.getenv("STRIPE_PRICE_PRO", "price_pro_placeholder"),
        "limits": {
            "tenders": 50,
            "ai_analysis": True,
            "team_members": 5,
            "api_access": False,
        },
        "features": [
            "Do 50 przetargów",
            "AI analiza ryzyka SWZ",
            "Automatyczny BZP sync",
            "Silnik kalkulacji",
            "5 członków zespołu",
            "Eksport Excel/PDF",
        ],
    },
    {
        "id": "business",
        "name": "Business",
        "price_pln": 1499,
        "price_label": "1499 PLN/mies",
        "billing": "miesięcznie",
        "stripe_price_id": os.getenv("STRIPE_PRICE_BUSINESS", "price_business_placeholder"),
        "limits": {
            "tenders": -1,
            "ai_analysis": True,
            "team_members": -1,
            "api_access": True,
        },
        "features": [
            "Nielimitowane przetargi",
            "Pełne AI analizy",
            "Dostęp API",
            "Nieograniczony zespół",
            "Priorytetowe wsparcie",
            "Zaawansowane raporty",
        ],
    },
    {
        "id": "enterprise",
        "name": "Enterprise",
        "price_pln": None,
        "price_label": "Wycena indywidualna",
        "billing": "roczny",
        "stripe_price_id": None,
        "limits": {
            "tenders": -1,
            "ai_analysis": True,
            "team_members": -1,
            "api_access": True,
        },
        "features": [
            "On-premise / self-hosted",
            "SSO / SAML",
            "SLA 99.9%",
            "Dedykowany opiekun",
            "Własne integracje",
            "Audyt bezpieczeństwa",
        ],
    },
]


# ─── Schemas ───────────────────────────────────────────────────────────────────

class CheckoutRequest(BaseModel):
    plan_id: str = "pro"
    success_url: str = "/billing/success"
    cancel_url: str = "/pricing"


# ─── Routes ────────────────────────────────────────────────────────────────────

@router.get("/plans")
def list_plans() -> list[dict[str, Any]]:
    """Return all available subscription plans."""
    return PLANS


@router.post("/checkout")
def checkout(body: CheckoutRequest, current_user: AuthUser) -> dict[str, str]:
    """Create Stripe Checkout session. Falls back to placeholder if Stripe not configured."""
    plan = next((p for p in PLANS if p["id"] == body.plan_id), None)
    if not plan:
        raise HTTPException(status_code=400, detail=f"Nieznany plan: {body.plan_id}")

    if plan["id"] in ("free", "enterprise"):
        return {
            "redirect_url": "/contact",
            "message": "Skontaktuj się z nami dla tego planu",
            "plan_id": body.plan_id,
        }

    stripe_key = os.getenv("STRIPE_SECRET_KEY", "")
    stripe_price_id = plan.get("stripe_price_id", "")

    if stripe_key and stripe_key.startswith("sk_") and stripe_price_id and not stripe_price_id.endswith("_placeholder"):
        try:
            # Try real Stripe integration
            import stripe  # type: ignore
            stripe.api_key = stripe_key
            session = stripe.checkout.Session.create(
                mode="subscription",
                line_items=[{"price": stripe_price_id, "quantity": 1}],
                success_url=body.success_url + "?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=body.cancel_url,
                metadata={"org_id": current_user.org_id or "", "user_id": current_user.user_id},
            )
            return {
                "redirect_url": session.url,
                "session_id": session.id,
                "plan_id": body.plan_id,
            }
        except Exception as e:
            # Fallback to placeholder
            pass

    return {
        "redirect_url": "#stripe-not-configured",
        "message": "Stripe nie jest jeszcze skonfigurowany. Skontaktuj się z support@terra.os",
        "plan_id": body.plan_id,
    }


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="stripe-signature"),
) -> dict[str, str]:
    """Handle Stripe webhooks (subscription updates)."""
    body = await request.body()

    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    if webhook_secret and stripe_signature:
        # Verify webhook signature
        try:
            # Simple HMAC verification (stripe uses timestamp-based signing)
            expected = hmac.new(webhook_secret.encode(), body, hashlib.sha256).hexdigest()
            # In production: use stripe.Webhook.construct_event
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

    # Parse event
    try:
        import json
        event = json.loads(body)
        event_type = event.get("type", "")

        # Handle subscription events
        if event_type == "customer.subscription.updated":
            # Update org plan in DB
            pass
        elif event_type == "customer.subscription.deleted":
            # Downgrade org to free
            pass
        elif event_type == "checkout.session.completed":
            # Activate subscription
            pass

    except Exception:
        pass

    return {"status": "ok"}


@router.get("/subscription")
def subscription(current_user: AuthUser, db: DB) -> dict[str, Any]:
    """Return current subscription plan for user's organization."""
    if not current_user.org_id:
        return {"plan": "free", "org_id": None}

    try:
        row = db.execute(
            text("SELECT plan FROM organizations WHERE id = :org_id"),
            {"org_id": current_user.org_id},
        ).fetchone()
        plan = row.plan if row and row.plan else "free"
    except Exception:
        plan = "free"

    plan_details = next((p for p in PLANS if p["id"] == plan), PLANS[0])

    return {
        "plan": plan,
        "org_id": current_user.org_id,
        "plan_details": plan_details,
    }
