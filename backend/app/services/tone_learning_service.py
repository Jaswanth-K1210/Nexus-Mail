"""
Nexus Mail — Passive Tone Learning Service
Architecture change based on Superhuman analysis:

Superhuman: Continuously scans outbox, builds high-dimensional vector
embeddings of the user's writing style WITHOUT requiring explicit feedback.

Our implementation:
- Periodically scans user's sent emails from Gmail
- AI extracts stylistic traits (formality, length, vocabulary, greeting style, etc.)
- Builds a rich, evolving tone profile stored in MongoDB
- Profile is automatically used by reply_draft.py and meeting responses
- No user intervention required — learns passively by observation
"""

from datetime import datetime, timezone

from app.core.database import get_database
from app.services.auth_service import AuthService
from app.ai_worker.ai_provider import ai_provider

import structlog

logger = structlog.get_logger(__name__)

TONE_ANALYSIS_PROMPT = """You are a linguistic style analyzer. Analyze the provided collection of emails written by the same person and extract their unique writing DNA.

You MUST return valid JSON with these fields:

{
    "formality_level": "casual" | "semi_formal" | "formal" | "very_formal",
    "avg_sentence_length": "short" | "medium" | "long",
    "greeting_style": "<how they typically start emails, e.g. 'Hey', 'Hi there', 'Dear'>",
    "sign_off_style": "<how they typically end, e.g. 'Thanks', 'Best', 'Cheers', 'Regards'>",
    "uses_exclamation_marks": true | false,
    "uses_emoji": true | false,
    "vocabulary_complexity": "simple" | "moderate" | "advanced",
    "typical_reply_length": "1-2 sentences" | "3-5 sentences" | "paragraph+",
    "directness": "very_direct" | "balanced" | "diplomatic",
    "humor_level": "none" | "occasional" | "frequent",
    "key_phrases": ["<phrases they frequently use>"],
    "overall_personality": "<2-sentence description of their email personality>",
    "confidence": 0.0-1.0
}

Be precise. Base your analysis ONLY on the actual text provided."""


class ToneLearningService:
    """
    Passive tone learning engine.
    Scans sent emails and builds an evolving stylistic profile.
    """

    def __init__(self):
        self.auth_service = AuthService()

    async def learn_from_sent_emails(
        self, user_id: str, max_emails: int = 25
    ) -> dict:
        """
        Scan user's sent emails from Gmail and build/update their tone profile.
        Called on first login and periodically in the background.
        """
        from googleapiclient.discovery import build

        credentials = await self.auth_service.get_user_credentials(user_id)
        if not credentials:
            raise ValueError("No Google credentials found")

        service = build("gmail", "v1", credentials=credentials)

        # Fetch recent sent emails
        sent_result = service.users().messages().list(
            userId="me",
            q="in:sent",
            maxResults=max_emails,
        ).execute()

        messages = sent_result.get("messages", [])
        if not messages:
            logger.info("No sent emails found for tone learning", user_id=user_id)
            return {"status": "no_sent_emails"}

        # Collect email bodies
        email_samples = []
        for msg_ref in messages[:max_emails]:
            try:
                msg = service.users().messages().get(
                    userId="me", id=msg_ref["id"], format="full"
                ).execute()

                body = self._extract_sent_body(msg)
                if body and len(body.strip()) > 20:
                    # Truncate very long emails to save tokens
                    email_samples.append(body[:500])
            except Exception as e:
                logger.warning("Failed to fetch sent email", error=str(e))
                continue

        if len(email_samples) < 3:
            logger.info(
                "Not enough sent emails for reliable tone analysis",
                user_id=user_id,
                count=len(email_samples),
            )
            return {"status": "insufficient_data", "count": len(email_samples)}

        # Combine samples for AI analysis
        combined = "\n\n---EMAIL---\n\n".join(email_samples[:20])

        # Run AI analysis
        tone_profile = await ai_provider.complete_json(
            system_prompt=TONE_ANALYSIS_PROMPT,
            user_prompt=f"Analyze these {len(email_samples)} emails written by the same person:\n\n{combined}",
            temperature=0.2,
        )

        # Store the learned profile
        db = get_database()
        await db.users.update_one(
            {"_id": user_id},
            {
                "$set": {
                    "tone_profile": tone_profile,
                    "tone_learned_at": datetime.now(timezone.utc),
                    "tone_email_count": len(email_samples),
                }
            },
        )

        logger.info(
            "Tone profile learned",
            user_id=user_id,
            emails_analyzed=len(email_samples),
            formality=tone_profile.get("formality_level"),
            personality=tone_profile.get("overall_personality", "")[:80],
        )

        return {
            "status": "learned",
            "emails_analyzed": len(email_samples),
            "profile": tone_profile,
        }

    async def get_tone_profile(self, user_id: str) -> dict | None:
        """Get the user's current tone profile."""
        db = get_database()
        user = await db.users.find_one(
            {"_id": user_id},
            {"tone_profile": 1, "tone_learned_at": 1, "tone_email_count": 1},
        )
        if not user or not user.get("tone_profile"):
            return None

        return {
            "profile": user["tone_profile"],
            "learned_at": user.get("tone_learned_at", "").isoformat() if user.get("tone_learned_at") else None,
            "emails_analyzed": user.get("tone_email_count", 0),
        }

    async def refresh_if_stale(self, user_id: str, max_age_days: int = 7) -> dict:
        """
        Check if the tone profile is stale and refresh if needed.
        Called automatically during email sync.
        """
        db = get_database()
        user = await db.users.find_one(
            {"_id": user_id},
            {"tone_learned_at": 1},
        )

        if not user:
            return {"status": "user_not_found"}

        learned_at = user.get("tone_learned_at")
        if learned_at:
            from datetime import timedelta
            age = datetime.now(timezone.utc) - learned_at
            if age < timedelta(days=max_age_days):
                return {"status": "fresh", "age_days": age.days}

        # Profile is stale or doesn't exist — re-learn
        return await self.learn_from_sent_emails(user_id)

    def _extract_sent_body(self, message: dict) -> str:
        """Extract the body text from a Gmail sent message."""
        import base64

        payload = message.get("payload", {})

        # Try direct body
        if payload.get("mimeType") == "text/plain":
            data = payload.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

        # Try parts
        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

        return ""
