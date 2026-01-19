
import os
import stripe
from dotenv import load_dotenv
from supabase import Client
from datetime import datetime, timezone

load_dotenv()

# Configure Stripe
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

class StripeService:
    def __init__(self, db: Client):
        self.db = db

    async def create_checkout_session(self, user_id: str, price_id: str):
        """
        Creates a Stripe Checkout Session for a subscription.
        """
        try:
            # 1. Get user email from Supabase (optional, for prefilling)
            # For simplicity, we just pass client_reference_id
            
            checkout_session = stripe.checkout.Session.create(
                client_reference_id=user_id,
                mode='subscription',
                payment_method_types=['card'],
                line_items=[
                    {
                        'price': price_id,
                        'quantity': 1,
                    },
                ],
                success_url=f"{FRONTEND_URL}/dashboard?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{FRONTEND_URL}/billing",
                subscription_data={
                    "metadata": {
                        "user_id": user_id
                    }
                }
            )
            return {"url": checkout_session.url}
        except Exception as e:
            raise e

    async def handle_webhook(self, payload, sig_header):
        """
        Handles Stripe Webhooks to update Supabase.
        """
        event = None

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
        except ValueError as e:
            # Invalid payload
            raise e
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            raise e

        # Handle the event
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            await self._handle_checkout_completed(session)
        elif event['type'] == 'customer.subscription.updated':
            subscription = event['data']['object']
            await self._handle_subscription_updated(subscription)
        elif event['type'] == 'customer.subscription.deleted':
            subscription = event['data']['object']
            await self._handle_subscription_deleted(subscription)

        return {"status": "success"}

    async def _handle_checkout_completed(self, session):
        """
        When a user pays, create/update their subscription in Supabase.
        """
        user_id = session.get('client_reference_id')
        stripe_sub_id = session.get('subscription')
        
        if not user_id or not stripe_sub_id:
            print("Webhook Error: Missing user_id or subscription_id")
            return

        # Fetch full subscription details from Stripe to get dates
        sub = stripe.Subscription.retrieve(stripe_sub_id)
        
        # Determine Tier from Price ID (Mock logic for now, ideally fetch from DB)
        price_id = sub['items']['data'][0]['price']['id']
        tier_id = self._get_tier_id_from_price(price_id)

        # Upsert Subscription
        data = {
            "user_id": user_id,
            "stripe_subscription_id": stripe_sub_id,
            "tier_id": tier_id,
            "status": "active",
            "current_period_start": datetime.fromtimestamp(sub['current_period_start'], timezone.utc).isoformat(),
            "current_period_end": datetime.fromtimestamp(sub['current_period_end'], timezone.utc).isoformat(),
            "is_active": True
        }
        
        # We assume one active sub per user for now
        # Check if exists
        existing = self.db.table("user_subscriptions").select("id").eq("user_id", user_id).execute()
        if existing.data:
            self.db.table("user_subscriptions").update(data).eq("user_id", user_id).execute()
        else:
            self.db.table("user_subscriptions").insert(data).execute()
            
        print(f"✅ Subscription activated for user {user_id}")

    async def _handle_subscription_updated(self, sub):
        # Update dates and status
        stripe_sub_id = sub['id']
        data = {
            "status": sub['status'],
            "current_period_start": datetime.fromtimestamp(sub['current_period_start'], timezone.utc).isoformat(),
            "current_period_end": datetime.fromtimestamp(sub['current_period_end'], timezone.utc).isoformat(),
            "is_active": sub['status'] == 'active'
        }
        self.db.table("user_subscriptions").update(data).eq("stripe_subscription_id", stripe_sub_id).execute()

    async def _handle_subscription_deleted(self, sub):
        stripe_sub_id = sub['id']
        data = {
            "status": "canceled",
            "is_active": False
        }
        self.db.table("user_subscriptions").update(data).eq("stripe_subscription_id", stripe_sub_id).execute()

    def _get_tier_id_from_price(self, price_id: str) -> str:
        # In a real app, query the 'tiers' table or use a config map
        # For MVP, we'll map hardcoded or look up
        # This requires the 'tiers' table to be populated with stripe_price_id
        res = self.db.table("tiers").select("id").eq("stripe_price_id", price_id).single().execute()
        if res.data:
            return res.data['id']
        return "tier_free" # Fallback
