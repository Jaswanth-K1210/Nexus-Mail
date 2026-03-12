"""
Nexus Mail — Thread Summarization Service
Summarizes entire 15+ message email threads, not just individual emails.
Provides full context, key decisions made, open questions, and action items.

This solves the problem where AI only summarizes the most recent message,
forcing the user to read the rest of the thread for context.
"""

from datetime import datetime, timezone
import json

from app.core.database import get_database
from app.ai_worker.ai_provider import ai_provider, TaskType

import structlog

logger = structlog.get_logger(__name__)

THREAD_SUMMARY_PROMPT = """You are an expert executive assistant.
You are given an entire email thread consisting of multiple back-and-forth messages.
Your task is to synthesize the entire conversation into a clear, actionable summary.

Analyze the thread and output valid JSON exactly matching this structure:
{
    "thread_summary": "<3-5 sentence summary of the entire back-and-forth>",
    "key_decisions": [
        "<decision 1>",
        "<decision 2>"
    ],
    "open_questions": [
        "<unresolved question 1>",
        "<unresolved question 2>"
    ],
    "action_items": [
        {"owner": "<name or 'User'>", "task": "<action description>"}
    ]
}

- Keep "key_decisions" strictly to what was agreed upon. If none, return empty list.
- Keep "open_questions" to things still needing an answer.
- For "action_items", identify who needs to do what.
- Return ONLY valid JSON, no markdown formatting or explanation.
"""


class ThreadService:
    """Service to generate and retrieve AI summaries for entire email threads."""

    async def get_thread_summary(self, user_id: str, thread_id: str, force_refresh: bool = False) -> dict:
        """
        Get the summary for a thread. Generates it if it doesn't exist
        or if the thread has new messages since last summary.
        """
        db = get_database()

        # Find the thread document
        thread_doc = await db.email_threads.find_one({
            "user_id": user_id,
            "thread_id": thread_id
        })

        # Find all emails in this thread to check message count
        emails_cursor = db.emails.find(
            {"user_id": user_id, "thread_id": thread_id},
            {"body_text": 1, "sender_name": 1, "received_at": 1}
        ).sort("received_at", 1)  # Chronological order
        
        emails = await emails_cursor.to_list(length=100)
        
        if not emails:
            return {"error": "No emails found for this thread."}

        current_message_count = len(emails)

        # Check if we need to generate/regenerate the summary
        needs_generation = (
            force_refresh or
            not thread_doc or
            not thread_doc.get("summary_data") or
            thread_doc.get("message_count_at_summary", 0) < current_message_count
        )

        if not needs_generation:
            return thread_doc.get("summary_data")

        # Compile the thread context for the LLM
        thread_text = self._compile_thread_context(emails)

        # Generate summary
        try:
            summary_data = await ai_provider.complete_json(
                system_prompt=THREAD_SUMMARY_PROMPT,
                user_prompt=f"Email Thread:\n\n{thread_text}",
                temperature=0.2,
                max_tokens=1500,
                task_type=TaskType.SUMMARIZATION,
            )
        except Exception as e:
            logger.error("Failed to generate thread summary", thread_id=thread_id, error=str(e))
            return {"error": "Failed to generate summary."}

        # Update or create the thread document
        update_data = {
            "summary_data": summary_data,
            "message_count_at_summary": current_message_count,
            "updated_at": datetime.now(timezone.utc)
        }

        await db.email_threads.update_one(
            {"user_id": user_id, "thread_id": thread_id},
            {"$set": update_data},
            upsert=True
        )

        logger.info(
            "Thread summary generated",
            user_id=user_id,
            thread_id=thread_id,
            messages=current_message_count
        )

        return summary_data

    def _compile_thread_context(self, emails: list[dict]) -> str:
        """Combines multiple emails into a single chronological text block."""
        context = []
        for i, email in enumerate(emails):
            sender = email.get("sender_name", "Unknown Sender")
            date_str = email.get("received_at", "Unknown Date")
            if isinstance(date_str, datetime):
                date_str = date_str.strftime("%Y-%m-%d %H:%M:%S")
                
            body = email.get("body_text", "")
            if not body:
                body = "[No text content]"
                
            # Truncate overly long individual messages
            if len(body) > 2000:
                body = body[:2000] + "... [truncated]"

            msg_block = f"--- Message {i+1} ---\nFrom: {sender}\nDate: {date_str}\n\n{body}\n"
            context.append(msg_block)

        full_text = "\n".join(context)
        
        # Prevent context window overflow
        MAX_CONTEXT_LENGTH = 12000
        if len(full_text) > MAX_CONTEXT_LENGTH:
            full_text = full_text[-MAX_CONTEXT_LENGTH:]
            full_text = "[... Earlier messages truncated ...]\n\n" + full_text

        return full_text
