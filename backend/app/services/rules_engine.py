"""
Nexus Mail — Natural Language Rules Engine
Users define email rules in plain English. LLM interprets semantically.

Inspired by Inbox Zero's "Cursor Rules for email" concept, but with:
- Meeting awareness (auto-accept/decline based on availability)
- Action chaining (multiple actions per rule)
- Confidence thresholds (require AI to be X% sure before executing)
- Match counting and history
"""

from datetime import datetime, timezone
from bson import ObjectId
from typing import Optional

from app.core.database import get_database
from app.ai_worker.ai_provider import ai_provider, TaskType

import structlog

logger = structlog.get_logger(__name__)

# ─── Prompt for LLM to compile natural language rules ───
RULE_COMPILER_PROMPT = """You are an email rule compiler. The user will give you a natural language instruction for handling emails.

Convert it into a structured JSON rule with these fields:

{
    "description": "<human-readable summary of what the rule does>",
    "conditions": {
        "sender_email": "<exact email or null>",
        "sender_domain": "<domain like @company.com or null>",
        "sender_name_contains": "<substring or null>",
        "subject_contains": "<substring or null>",
        "body_contains": "<substring or null>",
        "category": "<one of: important, requires_response, meeting_invitation, newsletter, promotional, social, transactional, spam, or null>",
        "is_meeting": true/false/null,
        "is_first_contact": true/false/null,
        "semantic_match": "<describe the semantic intent to match, e.g. 'sales pitch', 'investor communication', 'job application', or null>"
    },
    "actions": [
        {"type": "label", "value": "<label name>"},
        {"type": "archive"},
        {"type": "mark_read"},
        {"type": "mark_important"},
        {"type": "set_priority", "value": <0-100>},
        {"type": "draft_reply", "template": "<short reply instruction>"},
        {"type": "auto_accept_if_free"},
        {"type": "auto_decline"},
        {"type": "notify", "message": "<notification text>"},
        {"type": "skip_processing"}
    ],
    "confidence_threshold": 0.7
}

Rules for your output:
- Only include conditions that are relevant. Set irrelevant conditions to null.
- "semantic_match" is for complex intent-based matching — use it when the user describes intent rather than specific keywords.
- Actions should be an array. Include ALL actions the user describes.
- confidence_threshold defaults to 0.7 unless user specifies otherwise.
- For meeting-related rules, use "is_meeting": true and appropriate meeting actions.
- Return ONLY raw JSON. No markdown, no explanation."""


RULE_EVALUATOR_PROMPT = """You are an email rule evaluator. Given an email and a rule, determine if the email matches the rule conditions.

You MUST return valid JSON:
{
    "matches": true/false,
    "confidence": 0.0-1.0,
    "reason": "<why it matches or doesn't in 1 sentence>"
}

Be precise. Only return true if you are confident the email genuinely matches the rule intent."""


class RulesEngine:
    """
    Natural language email rules engine.
    Users write rules in English. LLM compiles to structured actions.
    During pipeline processing, rules are evaluated against incoming emails.
    """

    async def create_rule(self, user_id: str, rule_text: str) -> dict:
        """
        Create a new rule from natural language input.
        LLM compiles the text into structured conditions + actions.
        """
        db = get_database()

        # Compile the natural language rule via AI
        compiled = await ai_provider.complete_json(
            system_prompt=RULE_COMPILER_PROMPT,
            user_prompt=f"Compile this email rule:\n\n{rule_text}",
            temperature=0.1,
            task_type=TaskType.RULE_MATCHING,
        )

        rule_doc = {
            "user_id": user_id,
            "rule_text": rule_text,
            "description": compiled.get("description", rule_text),
            "conditions": compiled.get("conditions", {}),
            "actions": compiled.get("actions", []),
            "confidence_threshold": compiled.get("confidence_threshold", 0.7),
            "is_active": True,
            "match_count": 0,
            "last_matched": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

        result = await db.user_rules.insert_one(rule_doc)

        logger.info(
            "Rule created",
            rule_id=str(result.inserted_id),
            rule_text=rule_text[:80],
            actions=len(compiled.get("actions", [])),
        )

        return {
            "rule_id": str(result.inserted_id),
            "description": rule_doc["description"],
            "conditions": rule_doc["conditions"],
            "actions": rule_doc["actions"],
            "confidence_threshold": rule_doc["confidence_threshold"],
        }

    async def get_rules(self, user_id: str) -> list[dict]:
        """Get all rules for a user."""
        db = get_database()
        rules = []

        cursor = db.user_rules.find(
            {"user_id": user_id}
        ).sort("created_at", -1)

        async for rule in cursor:
            rules.append({
                "id": str(rule["_id"]),
                "rule_text": rule.get("rule_text", ""),
                "description": rule.get("description", ""),
                "conditions": rule.get("conditions", {}),
                "actions": rule.get("actions", []),
                "confidence_threshold": rule.get("confidence_threshold", 0.7),
                "is_active": rule.get("is_active", True),
                "match_count": rule.get("match_count", 0),
                "last_matched": rule.get("last_matched"),
                "created_at": rule["created_at"].isoformat(),
            })

        return rules

    async def update_rule(
        self, rule_id: str, user_id: str, rule_text: str | None = None,
        is_active: bool | None = None
    ) -> dict:
        """Update a rule — recompile if text changed, or toggle active state."""
        db = get_database()

        update_data = {"updated_at": datetime.now(timezone.utc)}

        if rule_text is not None:
            # Recompile the rule
            compiled = await ai_provider.complete_json(
                system_prompt=RULE_COMPILER_PROMPT,
                user_prompt=f"Compile this email rule:\n\n{rule_text}",
                temperature=0.1,
                task_type=TaskType.RULE_MATCHING,
            )
            update_data["rule_text"] = rule_text
            update_data["description"] = compiled.get("description", rule_text)
            update_data["conditions"] = compiled.get("conditions", {})
            update_data["actions"] = compiled.get("actions", [])
            update_data["confidence_threshold"] = compiled.get("confidence_threshold", 0.7)

        if is_active is not None:
            update_data["is_active"] = is_active

        result = await db.user_rules.update_one(
            {"_id": ObjectId(rule_id), "user_id": user_id},
            {"$set": update_data},
        )

        if result.modified_count == 0:
            raise ValueError("Rule not found")

        return {"status": "updated"}

    async def delete_rule(self, rule_id: str, user_id: str) -> dict:
        """Delete a rule."""
        db = get_database()
        result = await db.user_rules.delete_one(
            {"_id": ObjectId(rule_id), "user_id": user_id}
        )
        if result.deleted_count == 0:
            raise ValueError("Rule not found")
        return {"status": "deleted"}

    async def test_rule(
        self, user_id: str, rule_id: str, email_id: str
    ) -> dict:
        """Test a rule against a specific email to see if it matches."""
        db = get_database()

        rule = await db.user_rules.find_one(
            {"_id": ObjectId(rule_id), "user_id": user_id}
        )
        if not rule:
            raise ValueError("Rule not found")

        email = await db.emails.find_one(
            {"_id": ObjectId(email_id), "user_id": user_id}
        )
        if not email:
            raise ValueError("Email not found")

        match_result = await self._evaluate_rule(rule, email)

        return {
            "rule_text": rule.get("rule_text", ""),
            "email_subject": email.get("subject", ""),
            "matches": match_result["matches"],
            "confidence": match_result["confidence"],
            "reason": match_result["reason"],
            "would_execute_actions": rule.get("actions", []) if match_result["matches"] else [],
        }

    async def evaluate_all_rules(self, user_id: str, email_doc: dict) -> list[dict]:
        """
        Evaluate ALL active rules for a user against an incoming email.
        Called during the pipeline processing.
        Returns list of matched rules with their actions.
        """
        db = get_database()

        matched_rules = []
        cursor = db.user_rules.find(
            {"user_id": user_id, "is_active": True}
        )

        async for rule in cursor:
            try:
                match_result = await self._evaluate_rule(rule, email_doc)

                threshold = rule.get("confidence_threshold", 0.7)
                if match_result["matches"] and match_result["confidence"] >= threshold:
                    matched_rules.append({
                        "rule_id": str(rule["_id"]),
                        "rule_text": rule.get("rule_text", ""),
                        "actions": rule.get("actions", []),
                        "confidence": match_result["confidence"],
                        "reason": match_result["reason"],
                    })

                    # Update match count
                    await db.user_rules.update_one(
                        {"_id": rule["_id"]},
                        {
                            "$inc": {"match_count": 1},
                            "$set": {"last_matched": datetime.now(timezone.utc)},
                        },
                    )

            except Exception as e:
                logger.warning(
                    "Rule evaluation failed",
                    rule_id=str(rule["_id"]),
                    error=str(e),
                )
                continue

        return matched_rules

    async def execute_actions(
        self, user_id: str, email_id: str, actions: list[dict], email_doc: dict
    ) -> list[dict]:
        """
        Execute the actions from matched rules.
        Returns a list of action results.
        """
        db = get_database()
        results = []

        for action in actions:
            action_type = action.get("type")

            try:
                if action_type == "label":
                    await db.emails.update_one(
                        {"_id": ObjectId(email_id)},
                        {"$addToSet": {"labels": action.get("value", "custom")}},
                    )
                    results.append({"action": "label", "value": action.get("value"), "status": "done"})

                elif action_type == "archive":
                    await db.emails.update_one(
                        {"_id": ObjectId(email_id)},
                        {"$set": {"is_archived": True}},
                    )
                    results.append({"action": "archive", "status": "done"})

                elif action_type == "mark_read":
                    await db.emails.update_one(
                        {"_id": ObjectId(email_id)},
                        {"$set": {"is_read": True}},
                    )
                    results.append({"action": "mark_read", "status": "done"})

                elif action_type == "mark_important":
                    await db.emails.update_one(
                        {"_id": ObjectId(email_id)},
                        {"$set": {"category": "important"}},
                    )
                    results.append({"action": "mark_important", "status": "done"})

                elif action_type == "set_priority":
                    await db.emails.update_one(
                        {"_id": ObjectId(email_id)},
                        {"$set": {"priority_score": action.get("value", 50)}},
                    )
                    results.append({"action": "set_priority", "value": action.get("value"), "status": "done"})

                elif action_type == "notify":
                    from app.services.sse_service import push_to_user
                    await push_to_user(user_id, "rule_notification", {
                        "message": action.get("message", "Rule triggered"),
                        "email_subject": email_doc.get("subject", ""),
                        "sender": email_doc.get("sender_email", ""),
                    })
                    results.append({"action": "notify", "status": "done"})

                elif action_type == "skip_processing":
                    results.append({"action": "skip_processing", "status": "done"})

                elif action_type == "draft_reply":
                    # Generate a draft reply based on the rule's template
                    from app.services.draft_service import DraftService
                    draft_svc = DraftService()
                    from app.ai_worker.ai_provider import ai_provider as ai, TaskType as TT

                    reply_text = await ai.complete(
                        system_prompt="Write a brief email reply based on the template instruction. Write ONLY the reply text.",
                        user_prompt=f"Template: {action.get('template', 'polite acknowledgment')}\nOriginal email subject: {email_doc.get('subject', '')}\nOriginal sender: {email_doc.get('sender_name', '')}",
                        temperature=0.4,
                        task_type=TT.REPLY_DRAFT,
                    )

                    await draft_svc.create_draft(
                        user_id=user_id,
                        email_id=email_id,
                        draft_body=reply_text.strip(),
                        draft_type="reply",
                        ai_confidence=0.7,
                        recipient_email=email_doc.get("sender_email", ""),
                        recipient_name=email_doc.get("sender_name", ""),
                        subject=email_doc.get("subject", ""),
                        thread_id=email_doc.get("thread_id"),
                        source="rule",
                    )
                    results.append({"action": "draft_reply", "status": "done"})

                else:
                    results.append({"action": action_type, "status": "skipped", "reason": "unknown action"})

            except Exception as e:
                results.append({"action": action_type, "status": "error", "error": str(e)})
                logger.warning("Action execution failed", action=action_type, error=str(e))

        return results

    async def _evaluate_rule(self, rule: dict, email_doc: dict) -> dict:
        """
        Evaluate a single rule against an email.
        Uses deterministic checks first, then LLM for semantic matching.
        """
        conditions = rule.get("conditions", {})

        # ─── Fast deterministic checks first (no AI needed) ───
        sender_email = email_doc.get("sender_email", "").lower()
        subject = email_doc.get("subject", "").lower()
        body_text = email_doc.get("body_text", "").lower()

        # Sender email exact match
        if conditions.get("sender_email"):
            if conditions["sender_email"].lower() != sender_email:
                return {"matches": False, "confidence": 1.0, "reason": "Sender email doesn't match"}

        # Sender domain match
        if conditions.get("sender_domain"):
            domain = conditions["sender_domain"].lstrip("@").lower()
            if not sender_email.endswith(f"@{domain}"):
                return {"matches": False, "confidence": 1.0, "reason": "Sender domain doesn't match"}

        # Subject contains
        if conditions.get("subject_contains"):
            if conditions["subject_contains"].lower() not in subject:
                return {"matches": False, "confidence": 1.0, "reason": "Subject doesn't contain keyword"}

        # Body contains
        if conditions.get("body_contains"):
            if conditions["body_contains"].lower() not in body_text:
                return {"matches": False, "confidence": 1.0, "reason": "Body doesn't contain keyword"}

        # Category match
        if conditions.get("category"):
            if email_doc.get("category") != conditions["category"]:
                return {"matches": False, "confidence": 1.0, "reason": "Category doesn't match"}

        # Meeting flag
        if conditions.get("is_meeting") is not None:
            if email_doc.get("is_meeting_invitation") != conditions["is_meeting"]:
                return {"matches": False, "confidence": 1.0, "reason": "Meeting flag doesn't match"}

        # Sender name contains
        if conditions.get("sender_name_contains"):
            sender_name = email_doc.get("sender_name", "").lower()
            if conditions["sender_name_contains"].lower() not in sender_name:
                return {"matches": False, "confidence": 1.0, "reason": "Sender name doesn't match"}

        # First contact check
        if conditions.get("is_first_contact") is not None:
            db = get_database()
            previous = await db.emails.count_documents({
                "user_id": email_doc.get("user_id"),
                "sender_email": sender_email,
                "_id": {"$ne": email_doc.get("_id")},
            })
            is_first = previous == 0
            if is_first != conditions["is_first_contact"]:
                return {"matches": False, "confidence": 1.0, "reason": "First contact check failed"}

        # ─── Semantic matching via LLM (only if semantic_match is defined) ───
        if conditions.get("semantic_match"):
            result = await ai_provider.complete_json(
                system_prompt=RULE_EVALUATOR_PROMPT,
                user_prompt=(
                    f"Rule semantic condition: {conditions['semantic_match']}\n\n"
                    f"Email subject: {email_doc.get('subject', '')}\n"
                    f"Email sender: {email_doc.get('sender_name', '')} <{sender_email}>\n"
                    f"Email body (first 500 chars): {email_doc.get('body_text', '')[:500]}"
                ),
                temperature=0.1,
                task_type=TaskType.RULE_MATCHING,
            )
            return {
                "matches": result.get("matches", False),
                "confidence": result.get("confidence", 0),
                "reason": result.get("reason", "Semantic evaluation"),
            }

        # All deterministic conditions passed and no semantic needed
        return {"matches": True, "confidence": 1.0, "reason": "All conditions matched"}
