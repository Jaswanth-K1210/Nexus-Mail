"""
Nexus Mail — Inbox Triage Agent

Responsibilities:
- Email categorization (wraps existing classify.py)
- Priority scoring (wraps existing priority_service.py)
- Urgency estimation
- Sender importance analysis (wraps sender_intelligence.py)

Produces structured reasoning about WHY an email was classified a certain way.
"""

import time

from app.agents.base import BaseAgent, AgentResult, AgentStatus
from app.agents.state import WorkflowState

import structlog

logger = structlog.get_logger(__name__)


class TriageAgent(BaseAgent):
    """
    Inbox Triage Agent — first agent in the email processing graph.

    Combines classification, priority scoring, and sender analysis into a
    unified triage decision with reasoning trace.
    """

    name = "triage_agent"
    description = "Classifies emails, scores priority, and analyzes sender importance"
    max_retries = 2

    async def _execute(self, state: WorkflowState) -> AgentResult:
        from app.ai_worker.tasks.classify import classify_email
        from app.services.priority_service import PriorityService

        email = state.email
        user = state.user
        tool_invocations = []

        if not email:
            raise ValueError("No email context in state")

        # ─── Step 1: Sender Intelligence ──────────────────────────────────
        sender_profile = {}
        try:
            analytics_tool = self._tools.get("analytics")
            if analytics_tool:
                t0 = time.perf_counter()
                sender_result = await analytics_tool.execute(
                    action="sender_profile",
                    user_id=email.user_id,
                    sender_email=email.sender_email,
                )
                t1 = time.perf_counter()
                sender_profile = sender_result.output if sender_result.success else {}
                tool_invocations.append(self._record_tool_use(
                    "analytics", f"sender_profile({email.sender_email})",
                    f"relationship={sender_profile.get('relationship_strength', 0)}",
                    sender_result.success, (t1 - t0) * 1000,
                ))
        except Exception as e:
            logger.warning("Sender analysis failed (non-fatal)", error=str(e))

        # ─── Step 2: Classification (wraps existing task) ─────────────────
        classification = await classify_email(
            subject=email.subject,
            body=email.body,
            sender=email.sender_email,
            has_ics=email.has_ics,
            user_persona=user.user_persona if user else "",
            user_role=user.user_role if user else None,
        )

        # ─── Step 3: Priority Scoring ─────────────────────────────────────
        priority_service = PriorityService()
        enriched_doc = {
            **state.raw_email_doc,
            "category": classification.get("category"),
            "severity": classification.get("severity"),
            "is_meeting_invitation": classification.get("is_meeting_invitation", False),
            "subject": email.subject,
            "body_text": email.body,
            "sender_email": email.sender_email,
        }
        priority_score = await priority_service.score_email(email.user_id, enriched_doc)

        # ─── Step 4: Build Reasoning Trace ────────────────────────────────
        is_vip = sender_profile.get("is_vip", False)
        relationship = sender_profile.get("relationship_strength", 0)
        is_cold = sender_profile.get("is_cold_sender", False)
        category = classification.get("category", "important")

        reasoning_steps = [
            {
                "thought": f"Analyzing sender {email.sender_email}",
                "action": "Sender intelligence lookup",
                "observation": f"Relationship strength: {relationship}, VIP: {is_vip}, Cold: {is_cold}",
            },
            {
                "thought": f"Classifying email: '{email.subject[:60]}'",
                "action": "AI classification via LLM",
                "observation": f"Category: {category}, Severity: {classification.get('severity')}, Meeting: {classification.get('is_meeting_invitation')}",
            },
            {
                "thought": "Computing priority score using 5-signal algorithm",
                "action": "Priority scoring (relationship + urgency + category + recency + behavior)",
                "observation": f"Priority score: {priority_score}/100",
            },
        ]

        # Determine decision summary
        if is_vip and priority_score >= 80:
            decision = f"High-priority from VIP sender → category '{category}'"
        elif is_cold and priority_score < 30:
            decision = f"Cold sender, low priority → category '{category}', recommend skip"
        elif classification.get("is_meeting_invitation"):
            decision = f"Meeting invitation detected → routing to Meeting Intelligence Agent"
        else:
            decision = f"Standard triage → category '{category}', priority {priority_score}/100"

        reasoning = self._build_reasoning(
            decision=decision,
            reason=f"Sender relationship: {relationship:.2f}, Category: {category}, Severity: {classification.get('severity')}, Confidence: {classification.get('confidence', 0)}",
            confidence=classification.get("confidence", 0.5),
            steps=reasoning_steps,
        )

        # ─── Build Output ─────────────────────────────────────────────────
        output = {
            "classification": classification,
            "category": category,
            "severity": classification.get("severity", 3),
            "suggested_action": classification.get("suggested_action", "REVIEW ONLY"),
            "is_meeting_invitation": classification.get("is_meeting_invitation", False),
            "priority_score": priority_score,
            "sender_profile": {
                "relationship_strength": relationship,
                "is_vip": is_vip,
                "is_cold_sender": is_cold,
                "total_emails": sender_profile.get("total_emails", 0),
            },
            "_decision": decision,
        }

        # Update the workflow state with triage results
        state.category = category
        state.severity = classification.get("severity", 3)
        state.suggested_action = classification.get("suggested_action", "REVIEW ONLY")
        state.is_meeting = classification.get("is_meeting_invitation", False)
        state.priority_score = priority_score
        state.sender_profile = sender_profile

        return AgentResult(
            agent_name=self.name,
            output=output,
            reasoning=reasoning,
            tool_invocations=tool_invocations,
        )
