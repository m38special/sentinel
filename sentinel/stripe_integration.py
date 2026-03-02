#!/usr/bin/env python3
"""
Stripe Integration for Liquid Sound
Subscription payments
"""
import os
import json
import stripe
from datetime import datetime, timedelta
from typing import Dict, Optional

# Configure Stripe
stripe.api_key = os.getenv("STRIPE_API_KEY", "")

# Product pricing
PRICES = {
    "starter": {
        "price_id": os.getenv("STRIPE_STARTER_PRICE_ID", "price_starter"),
        "amount": 2900,  # $29.00
        "interval": "month",
    },
    "pro": {
        "price_id": os.getenv("STRIPE_PRO_PRICE_ID", "price_pro"),
        "amount": 9900,  # $99.00
        "interval": "month",
    },
    "vip": {
        "price_id": os.getenv("STRIPE_VIP_PRICE_ID", "price_vip"),
        "amount": 29900,  # $299.00
        "interval": "month",
    },
}


def create_customer(email: str, metadata: Dict = None) -> Dict:
    """Create Stripe customer"""
    try:
        customer = stripe.Customer.create(
            email=email,
            metadata=metadata or {},
        )
        return {"success": True, "customer_id": customer.id}
    except stripe.error.StripeError as e:
        return {"success": False, "error": str(e)}


def create_checkout_session(
    customer_id: str,
    price_id: str,
    success_url: str,
    cancel_url: str,
    metadata: Dict = None,
) -> Dict:
    """Create Stripe checkout session"""
    try:
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata or {},
        )
        return {"success": True, "session_id": session.id, "url": session.url}
    except stripe.error.StripeError as e:
        return {"success": False, "error": str(e)}


def create_portal_session(customer_id: str, return_url: str) -> Dict:
    """Create customer portal session"""
    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        return {"success": True, "url": session.url}
    except stripe.error.StripeError as e:
        return {"success": False, "error": str(e)}


def get_subscription(subscription_id: str) -> Dict:
    """Get subscription details"""
    try:
        sub = stripe.Subscription.retrieve(subscription_id)
        return {
            "success": True,
            "status": sub.status,
            "current_period_end": sub.current_period_end,
            "plan": sub.items.data[0].price.id,
        }
    except stripe.error.StripeError as e:
        return {"success": False, "error": str(e)}


def cancel_subscription(subscription_id: str, immediately: bool = False) -> Dict:
    """Cancel subscription"""
    try:
        if immediately:
            sub = stripe.Subscription.delete(subscription_id)
        else:
            sub = stripe.Subscription.modify(subscription_id, cancel_at_period_end=True)
        return {"success": True, "status": sub.status}
    except stripe.error.StripeError as e:
        return {"success": False, "error": str(e)}


def handle_webhook(payload: bytes, signature: str, webhook_secret: str) -> Dict:
    """Handle Stripe webhook"""
    try:
        event = stripe.Webhook.construct_event(
            payload, signature, webhook_secret
        )
        
        # Handle events
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            return {"event": "payment_success", "customer": session.get("customer")}
        
        elif event["type"] == "customer.subscription.deleted":
            return {"event": "subscription_cancelled"}
        
        elif event["type"] == "invoice.payment_failed":
            return {"event": "payment_failed"}
        
        return {"event": "unknown"}
    
    except stripe.error.SignatureVerificationError:
        return {"error": "Invalid signature"}
    except Exception as e:
        return {"error": str(e)}


# Subscription tiers mapping
TIER_STRIPE_PRICE = {
    "starter": os.getenv("STRIPE_STARTER_PRICE_ID"),
    "pro": os.getenv("STRIPE_PRO_PRICE_ID"),
    "vip": os.getenv("STRIPE_VIP_PRICE_ID"),
}


def get_tier_from_price(price_id: str) -> Optional[str]:
    """Map Stripe price to tier"""
    for tier, sid in TIER_STRIPE_PRICE.items():
        if sid == price_id:
            return tier
    return None


if __name__ == "__main__":
    print("Stripe Integration Ready")
    print(f"Prices configured: {list(PRICES.keys())}")
