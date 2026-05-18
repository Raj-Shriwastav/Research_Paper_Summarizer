"""
Database Client — Supabase integration for digest storage and user preferences.

Handles digest CRUD, user preference management, and auto-cleanup of old records.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from supabase import create_client, Client

from backend.config import SupabaseConfig

logger = logging.getLogger(__name__)


class DatabaseClient:
    """Supabase database client for the Research Paper Summarizer."""

    def __init__(self, config: SupabaseConfig):
        if not config.url or not config.service_key:
            raise ValueError(
                "Supabase URL and Service Key are required. "
                "Please add SUPABASE_URL and SUPABASE_SERVICE_KEY to your .env file."
            )
        self.client: Client = create_client(config.url, config.service_key)
        logger.info("Supabase database client initialized.")

    # ──────────────────────────────────────────────
    # Digest CRUD
    # ──────────────────────────────────────────────

    def save_digest(
        self,
        topic: str,
        digest_date: str,
        cadence: str,
        markdown_content: str,
        html_content: str = "",
        paper_count: int = 0,
        word_count: int = 0,
        metadata: Dict[str, Any] = None,
    ) -> Optional[Dict]:
        """Save a digest to the database. Upserts on (topic, cadence, digest_date)."""
        try:
            data = {
                "topic": topic,
                "digest_date": digest_date,
                "cadence": cadence,
                "markdown_content": markdown_content,
                "html_content": html_content,
                "paper_count": paper_count,
                "word_count": word_count,
                "metadata": metadata or {},
            }
            result = (
                self.client.table("digests")
                .upsert(data, on_conflict="topic,cadence,digest_date")
                .execute()
            )
            logger.info(f"Saved {cadence} digest for '{topic}' on {digest_date}.")
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to save digest: {e}")
            return None

    def get_digests(
        self,
        topic: Optional[str] = None,
        cadence: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict]:
        """Retrieve recent digests, optionally filtered by topic and cadence."""
        try:
            query = self.client.table("digests").select("*")
            if topic:
                query = query.eq("topic", topic)
            if cadence:
                query = query.eq("cadence", cadence)
            result = query.order("digest_date", desc=True).limit(limit).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to fetch digests: {e}")
            return []

    def get_weekly_digests(self, topic: str) -> List[Dict]:
        """Fetch all daily digests from the current week for aggregation."""
        try:
            today = datetime.now()
            # Monday of this week
            start_of_week = today - timedelta(days=today.weekday())
            result = (
                self.client.table("digests")
                .select("*")
                .eq("topic", topic)
                .eq("cadence", "daily")
                .gte("digest_date", start_of_week.strftime("%Y-%m-%d"))
                .lte("digest_date", today.strftime("%Y-%m-%d"))
                .order("digest_date", desc=False)
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to fetch weekly digests: {e}")
            return []

    def get_monthly_digests(self, topic: str) -> List[Dict]:
        """Fetch all daily digests from the current month for aggregation."""
        try:
            today = datetime.now()
            start_of_month = today.replace(day=1)
            result = (
                self.client.table("digests")
                .select("*")
                .eq("topic", topic)
                .eq("cadence", "daily")
                .gte("digest_date", start_of_month.strftime("%Y-%m-%d"))
                .lte("digest_date", today.strftime("%Y-%m-%d"))
                .order("digest_date", desc=False)
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to fetch monthly digests: {e}")
            return []

    def cleanup_old_digests(self, days: int = 45) -> int:
        """Delete digests older than `days` days. Returns count of deleted rows."""
        try:
            cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            result = (
                self.client.table("digests")
                .delete()
                .lt("digest_date", cutoff)
                .execute()
            )
            count = len(result.data) if result.data else 0
            if count > 0:
                logger.info(f"Cleaned up {count} digests older than {days} days.")
            return count
        except Exception as e:
            logger.error(f"Failed to cleanup old digests: {e}")
            return 0

    # ──────────────────────────────────────────────
    # User Preferences
    # ──────────────────────────────────────────────

    def get_user_preferences(self, user_id: str) -> Optional[Dict]:
        """Get a user's subscription preferences."""
        try:
            result = (
                self.client.table("user_preferences")
                .select("*")
                .eq("user_id", user_id)
                .single()
                .execute()
            )
            return result.data
        except Exception as e:
            logger.error(f"Failed to fetch user preferences: {e}")
            return None

    def update_user_preferences(self, user_id: str, prefs: Dict) -> Optional[Dict]:
        """Update a user's subscription preferences."""
        try:
            prefs["updated_at"] = datetime.now().isoformat()
            result = (
                self.client.table("user_preferences")
                .update(prefs)
                .eq("user_id", user_id)
                .execute()
            )
            logger.info(f"Updated preferences for user {user_id}.")
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to update user preferences: {e}")
            return None

    def get_subscribers(self, cadence: str) -> List[Dict]:
        """
        Get all users subscribed to a given cadence (daily/weekly/monthly).
        Returns list of dicts with user email and preferences.
        """
        try:
            result = (
                self.client.table("user_preferences")
                .select("*, users(email, delivery_email, display_name)")
                .contains("cadence", [cadence])
                .eq("email_enabled", True)
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to fetch subscribers for '{cadence}': {e}")
            return []

    def create_user_with_defaults(self, user_id: str, email: str, display_name: str = "") -> bool:
        """Create a new user and their default preferences on first login."""
        try:
            # Insert user
            self.client.table("users").upsert({
                "id": user_id,
                "email": email,
                "display_name": display_name or email.split("@")[0],
            }).execute()

            # Insert default preferences
            self.client.table("user_preferences").upsert({
                "user_id": user_id,
                "topics": ["Artificial Intelligence"],
                "cadence": ["daily", "weekly", "monthly"],
                "max_papers_per_digest": 2,
                "email_enabled": True,
            }).execute()

            logger.info(f"Created user and default preferences for {email}.")
            return True
        except Exception as e:
            logger.error(f"Failed to create user {email}: {e}")
            return False

    def update_delivery_log(self, log_id: str, status: str, error_message: str = None) -> bool:
        """Update the status of an email_delivery_log record."""
        try:
            data = {"status": status}
            if error_message:
                data["error_message"] = error_message
                
            self.client.table("email_delivery_log").update(data).eq("id", log_id).execute()
            logger.info(f"Updated delivery log {log_id} to status {status}.")
            return True
        except Exception as e:
            logger.error(f"Failed to update delivery log {log_id}: {e}")
            return False
