"""
Nexus Mail — Smart Priority Scoring Service
5-signal algorithm combining Superhuman's behavioral velocity + Inbox Zero's LLM classification.

Every email gets a 0-100 priority score:
  - Sender Relationship (30%): reply frequency, response time, thread depth
  - Content Urgency (25%): AI detects deadlines, ASAP, time-sensitive language
  - Category Weight (20%): important=90, requires_response=80, meeting=85, newsletter=10
  - Recency Decay (15%): exponential decay as email ages
  - User Behavior (10%): how fast user typically opens this sender's emails
"""

import math
from datetime import datetime, timezone

from app.core.database import get_database

import structlog

logger = structlog.get_logger(__name__)

# ─── Category weight mapping (0-100) ───
# Shared categories have fixed weights. Role-specific categories default to 70
# (work-relevant) unless overridden here.
CATEGORY_WEIGHTS = {
    # Shared
    "important": 90,
    "requires_response": 80,
    "meeting_invitation": 85,
    "transactional": 40,
    "social": 30,
    "newsletter": 15,
    "promotional": 10,
    "spam": 0,
    # High-priority role categories (require action)
    "task_assigned": 85, "approval_required": 85, "court_notice": 90,
    "investor_communication": 85, "patient_communication": 85,
    "case_update": 85, "work_order": 80, "listing_inquiry": 80,
    "lead_inbound": 80, "brand_deal": 80, "new_project_inquiry": 80,
    "donor_communication": 80, "audit_compliance": 85,
    "assignment": 80, "exam_notice": 85,
    # Medium-priority (awareness needed)
    "cold_outreach": 20, "fan_dm": 25, "platform_notification": 30,
    "platform_update": 30, "campus_event": 35,
}
# Anything not listed defaults to 70 (assumed work-relevant for the role)


class PriorityService:
    """Calculates a 0-100 priority score for every email using 5 signals."""

    async def score_email(self, user_id: str, email_doc: dict) -> int:
        """
        Calculate the composite priority score for an email.
        Returns 0-100 integer.
        """
        db = get_database()
        sender_email = email_doc.get("sender_email", "").lower()

        # ─── Signal 1: Sender Relationship (30%) ───
        relationship_score = await self._sender_relationship(db, user_id, sender_email)

        # ─── Signal 2: Content Urgency (25%) ───
        urgency_score = self._content_urgency(email_doc)

        # ─── Signal 3: Category Weight (20%) ───
        category = email_doc.get("category", "")
        category_score = CATEGORY_WEIGHTS.get(category, 70)

        # ─── Signal 4: Recency Decay (15%) ───
        recency_score = self._recency_decay(email_doc)

        # ─── Signal 5: User Behavior (10%) ───
        behavior_score = await self._user_behavior(db, user_id, sender_email)

        # Weighted composite
        composite = (
            relationship_score * 0.30
            + urgency_score * 0.25
            + category_score * 0.20
            + recency_score * 0.15
            + behavior_score * 0.10
        )

        priority = max(0, min(100, round(composite)))

        # Guarantee critical categories always land in the Priority Inbox (score >= 50)
        if category in ["important", "meeting_invitation", "requires_response"]:
            priority = max(priority, 55)

        logger.debug(
            "Priority scored",
            sender=sender_email,
            priority=priority,
            signals={
                "relationship": relationship_score,
                "urgency": urgency_score,
                "category": category_score,
                "recency": recency_score,
                "behavior": behavior_score,
            },
        )

        return priority

    async def score_and_store(self, user_id: str, email_id: str, email_doc: dict) -> int:
        """Score an email and store the priority in the DB."""
        from bson import ObjectId
        db = get_database()

        score = await self.score_email(user_id, email_doc)

        await db.emails.update_one(
            {"_id": ObjectId(email_id), "user_id": user_id},
            {"$set": {"priority_score": score}},
        )

        return score

    async def _sender_relationship(self, db, user_id: str, sender_email: str) -> float:
        """
        How strong is the relationship with this sender? (0-100)
        Based on: total email count, reply count, thread depth.
        """
        # Total emails from this sender
        total = await db.emails.count_documents({
            "user_id": user_id,
            "sender_email": sender_email,
        })

        if total == 0:
            # First contact — neutral-low score
            return 25.0

        # Emails where user has a reply_draft or the sender appears in conversations
        thread_ids = await db.emails.distinct("thread_id", {
            "user_id": user_id,
            "sender_email": sender_email,
        })
        thread_count = len(thread_ids) if thread_ids else 0

        # Scoring formula: log scale to avoid extreme senders dominating
        email_factor = min(100, math.log2(total + 1) * 15)  # 0-100
        thread_factor = min(100, thread_count * 10)  # 0-100

        return (email_factor * 0.6) + (thread_factor * 0.4)

    def _content_urgency(self, email_doc: dict) -> float:
        """
        How urgent is the content? (0-100)
        Based on: urgency keywords, severity rating, deadlines.
        """
        subject = (email_doc.get("subject", "") + " " + email_doc.get("body_text", "")[:500]).lower()

        score = 30.0  # baseline

        # High urgency signals
        urgent_keywords = [
            "urgent", "asap", "immediately", "critical", "deadline",
            "time-sensitive", "action required", "by end of day",
            "by eod", "by tomorrow", "by tonight", "due today", "emergency",
        ]
        for kw in urgent_keywords:
            if kw in subject:
                score += 15
                break

        # Medium urgency signals
        medium_keywords = [
            "important", "reminder", "follow up", "follow-up",
            "please respond", "need your input", "waiting on",
        ]
        for kw in medium_keywords:
            if kw in subject:
                score += 8
                break

        # AI severity multiplier (1-5 scale)
        severity = email_doc.get("severity", 3)
        try:
            severity = int(severity)
        except (ValueError, TypeError):
            severity = 3
            
        if severity:
            score += (severity - 3) * 10  # 1→-20, 2→-10, 3→0, 4→+10, 5→+20

        return max(0, min(100, score))

    def _recency_decay(self, email_doc: dict) -> float:
        """
        How recent is this email? (0-100)
        Exponential decay: fresh = 100, 1 day = 80, 3 days = 50, 7 days = 20.
        """
        received_at = email_doc.get("received_at")
        if not received_at:
            return 50.0

        if isinstance(received_at, str):
            from dateutil import parser
            received_at = parser.parse(received_at)

        now = datetime.now(timezone.utc)
        if received_at.tzinfo is None:
            received_at = received_at.replace(tzinfo=timezone.utc)

        age_hours = max(0, (now - received_at).total_seconds() / 3600)

        # Exponential decay: half-life of ~36 hours
        score = 100 * math.exp(-0.02 * age_hours)

        return max(0, min(100, score))

    async def _user_behavior(self, db, user_id: str, sender_email: str) -> float:
        """
        How fast does the user typically engage with this sender's emails? (0-100)
        Based on read rate.
        """
        total = await db.emails.count_documents({
            "user_id": user_id,
            "sender_email": sender_email,
        })

        if total == 0:
            return 50.0

        read = await db.emails.count_documents({
            "user_id": user_id,
            "sender_email": sender_email,
            "is_read": True,
        })

        read_rate = read / total if total > 0 else 0
        return read_rate * 100
