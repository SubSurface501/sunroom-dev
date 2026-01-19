import logging
from datetime import datetime, timezone
from supabase import Client
from db import schemas # For Pydantic models

logger = logging.getLogger(__name__)

class QuotaExceededError(Exception):
    """Raised when a user tries to perform an action beyond their tier limits."""
    pass

# Define a virtual unlimited tier for Dev/Fallback
DEV_UNLIMITED_TIER = schemas.Tier(
    id=999,
    name="Dev Tier",
    price_monthly=0.0,
    max_documents=None, # Unlimited
    max_volumes=None, # Unlimited
    max_audio_minutes=None, # Unlimited
    max_llm_tokens=None, # Unlimited
    max_image_generations=None # Unlimited
)

class UsageGatekeeper:
    def __init__(self, db: Client, user_id: str):
        self.db = db
        self.user_id = user_id
        self.subscription: schemas.UserSubscription | None = None
        self.tier: schemas.Tier | None = None
        self._load_subscription_and_tier()

    def _load_subscription_and_tier(self):
        """Fetches the current active subscription + tier details using Supabase client."""
        now_utc = datetime.now(timezone.utc)
        response = self.db.table("user_subscriptions").select("*, tiers(*)").eq("user_id", self.user_id).eq("is_active", True).gte("cycle_end_date", now_utc.isoformat()).limit(1).execute()
        
        if response.data:
            sub_data = response.data[0]
            self.subscription = schemas.UserSubscription(**sub_data)
            
            # Extract tier data which is embedded due to `tiers(*)`
            if sub_data.get('tiers'):
                tier_data = sub_data['tiers']
                self.tier = schemas.Tier(**tier_data)
            else:
                logger.warning(f"No tier found for subscription {self.subscription.id}. Defaulting to Dev Tier (Unlimited).")
                self.tier = DEV_UNLIMITED_TIER
        else:
            logger.info(f"No active subscription found for user {self.user_id}. Defaulting to Dev Tier (Unlimited).")
            # In Dev/Self-Hosted mode, we default to unlimited if no sub exists.
            self.tier = DEV_UNLIMITED_TIER

    def _get_current_usage(self, activity_type: str) -> int:
        """Sums up usage logs for the current billing cycle using Supabase client."""
        if not self.subscription:
            return 0 # No subscription, effectively unlimited or no usage to track

        response = self.db.table("usage_logs").select("quantity_used").eq("user_id", self.user_id).eq("activity_type", activity_type).gte("created_at", self.subscription.cycle_start_date.isoformat()).execute()
        
        total = sum(item['quantity_used'] for item in response.data) if response.data else 0
        return total

    # ------------------------------------------------------------------
    # GATE CHECKS (Call these BEFORE processing)
    # ------------------------------------------------------------------

    def check_ingest_document(self):
        """Checks document ingestion against the tier limit."""
        if not self.tier:
            raise QuotaExceededError("No active subscription.")
            
        if self.tier.max_documents is None:
            return True # Unlimited

        usage = self._get_current_usage('INGEST_DOC')
        if usage >= self.tier.max_documents:
             raise QuotaExceededError(
                f"Document limit reached ({usage}/{self.tier.max_documents}). Upgrade to Creator Tier."
            )
        return True

    def check_media_processing(self, duration_seconds: int):
        """Checks if adding this file fits in the monthly minutes budget."""
        if not self.tier:
            raise QuotaExceededError("No active subscription.")

        if self.tier.max_audio_minutes is None:
            return True # Unlimited

        usage_seconds = self._get_current_usage('PROCESS_MEDIA')
        projected_seconds = usage_seconds + duration_seconds
        
        limit_seconds = self.tier.max_audio_minutes * 60
        
        if projected_seconds > limit_seconds:
            remaining_seconds = limit_seconds - usage_seconds
            raise QuotaExceededError(
                f"Media limit exceeded. You have {remaining_seconds // 60} minutes remaining, "
                f"but this file is {duration_seconds // 60} minutes."
            )
        return True

    def check_generation(self):
        """Checks volume generation against the tier limit."""
        if not self.tier:
            raise QuotaExceededError("No active subscription.")

        if self.tier.max_volumes is None:
            return True # Unlimited

        usage = self._get_current_usage('GENERATE_VOLUME')
        if usage >= self.tier.max_volumes:
            raise QuotaExceededError(
                f"Synthesis limit reached ({usage}/{self.tier.max_volumes})."
            )
        return True

    # ------------------------------------------------------------------
    # LEDGER ACTIONS (Call these AFTER processing succeeds)
    # ------------------------------------------------------------------

    def log_ingest(self, project_id: str, file_name: str):
        self._write_log('INGEST_DOC', 1, project_id, {"file": file_name})

    def log_media(self, project_id: str, duration_seconds: int, file_name: str):
        self._write_log('PROCESS_MEDIA', duration_seconds, project_id, {"file": file_name, "seconds": duration_seconds})

    def log_generation(self, project_id: str, volume_title: str):
        self._write_log('GENERATE_VOLUME', 1, project_id, {"title": volume_title})

    def _write_log(self, activity: str, quantity: int, project_id: str | None, meta: dict):
        log_data = {
            "user_id": self.user_id,
            "project_id": project_id,
            "activity_type": activity,
            "quantity_used": quantity,
            "metadata": meta
        }
        try:
            self.db.table("usage_logs").insert(log_data).execute()
        except Exception as e:
            logger.error(f"Failed to log usage: {e}")
            # Depending on policy, we might re-raise or just log the error.
            # For now, we log but allow the main process to continue.