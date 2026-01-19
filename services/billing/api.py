
import os
import stripe
import logging
from fastapi import APIRouter, Depends, Header, Request, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from auth.dependencies import get_current_user
from db import crud
from db.session import get_db

# Initialize logger
logger = logging.getLogger(__name__)

router = APIRouter()

# Ensure your Stripe API key is set
stripe.api_key = os.getenv("STRIPE_API_KEY")
webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None), db: Session = Depends(get_db)):
    """
    Stripe webhook handler to process events.
    """
    if not stripe_signature or not webhook_secret:
        logger.warning("Stripe webhook called without signature or secret.")
        raise HTTPException(status_code=400, detail="Missing Stripe signature or webhook secret.")

    try:
        payload = await request.body()
        event = stripe.Webhook.construct_event(
            payload=payload, sig_header=stripe_signature, secret=webhook_secret
        )
    except ValueError as e:
        logger.error(f"Invalid webhook payload: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid payload: {e}")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid webhook signature: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid signature: {e}")

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_checkout_session_completed(session, db)
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        handle_subscription_deleted(subscription, db)
    else:
        logger.info(f"Unhandled Stripe event type received: {event['type']}")

    return {"status": "success"}


def handle_checkout_session_completed(session: dict, db: Session):
    """
    Handles the checkout.session.completed event.
    Creates or updates a user's subscription in the database.
    """
    client_reference_id = session.get("client_reference_id")
    if not client_reference_id:
        logger.error("CRITICAL: client_reference_id not found in completed checkout session.", extra={"session_id": session.get("id")})
        return

    user_id = client_reference_id
    stripe_subscription_id = session.get("subscription")
    stripe_customer_id = session.get("customer")
    
    logger.info(f"Processing successful checkout for user_id: {user_id}", extra={"stripe_subscription_id": stripe_subscription_id})

    line_items = stripe.checkout.Session.list_line_items(session["id"], limit=1)
    if not line_items.data:
        logger.error(f"No line items found for session {session['id']}. Cannot determine tier.", extra={"session_id": session.get("id")})
        return
    
    price_id = line_items.data[0].price.id
    
    tier = crud.get_tier_by_stripe_price_id(db, price_id)
    if not tier:
        logger.error(f"Tier with Stripe Price ID '{price_id}' not found in database.", extra={"session_id": session.get("id")})
        # As a fallback, let's grab the first available paid tier.
        # THIS IS NOT PRODUCTION-READY LOGIC.
        tier = db.query(crud.Tier).filter(crud.Tier.name != "Free").first()
        if not tier:
            logger.critical("No fallback tiers available. User was charged but not provisioned.", extra={"session_id": session.get("id")})
            return

    subscription_data = {
        "user_id": user_id,
        "tier_id": tier.id,
        "stripe_subscription_id": stripe_subscription_id,
        "stripe_customer_id": stripe_customer_id,
        "is_active": True,
    }
    
    crud.create_or_update_user_subscription(db, subscription_data)
    logger.info(f"Successfully processed and saved subscription for user {user_id}.", extra={"tier_id": tier.id, "stripe_subscription_id": stripe_subscription_id})


def handle_subscription_deleted(subscription: dict, db: Session):
    """
    Handles the customer.subscription.deleted event.
    Marks a user's subscription as inactive.
    """
    stripe_subscription_id = subscription.get("id")
    crud.deactivate_subscription(db, stripe_subscription_id)
    logger.info(f"Successfully deactivated subscription {stripe_subscription_id}.")

class CreateCheckoutSessionRequest(BaseModel):
    price_id: str
    
@router.post("/create-checkout-session")
async def create_checkout_session(
    request: CreateCheckoutSessionRequest,
    user: dict = Depends(get_current_user)
):
    """
    Creates a Stripe Checkout Session for a user to subscribe to a new plan.
    """
    logger.info(f"User {user.id} is creating a checkout session for price {request.price_id}")
    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    "price": request.price_id,
                    "quantity": 1,
                },
            ],
            mode="subscription",
            success_url="https://www.thesunroom.ca/dashboard?subscribe=success",
            cancel_url="https://www.thesunroom.ca/dashboard?subscribe=cancel",
            client_reference_id=user.id,
        )
        return {"url": checkout_session.url}
    except Exception as e:
        logger.error(f"Failed to create Stripe checkout session for user {user.id}: {e}", exc_info=True)
        # Also capture to Sentry
        sentry_sdk.capture_exception(e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create Stripe checkout session: {str(e)}",
        )

