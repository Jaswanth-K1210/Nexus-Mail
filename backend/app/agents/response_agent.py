"""
Nexus Mail — Response Generation Agent

Responsibilities:
- Draft strategy determination
- Auto-reply for low-priority emails
- Corporate Shield Protocol for VIP senders
- On-demand draft metadata preparation
"""

from app.agents.base import BaseAgent, AgentResult
from app.agents.state import WorkflowState
import structlog

logger = structlog.get_logger(__name__)


class ResponseAgent(BaseAgent):
    name = "response_agent"
    description = "Generates contextual email drafts and manages auto-reply logic"
    max_retries = 1

    async def _execute(self, state: WorkflowState) -> AgentResult:
        email = state.email
        if not email:
            raise ValueError("No email context in state")

        category = state.category or "important"
        priority = state.priority_score
        is_vip = state.sender_profile.get("is_vip", False)
        suggested_action = state.suggested_action or "REVIEW ONLY"

        auto_reply_eligible = (
            priority < 35
            and suggested_action != "ACTION REQUIRED"
            and category not in ("important", "meeting_invitation", "spam")
        )
        auto_reply_result = None

        if auto_reply_eligible:
            try:
                from app.services.auto_reply_service import AutoReplyService
                svc = AutoReplyService()
                enriched = {**state.raw_email_doc, "category": category, "priority_score": priority, "suggested_action": suggested_action}
                if await svc.should_auto_reply(email.user_id, state.raw_email_doc):
                    auto_reply_result = await svc.generate_and_send(email.user_id, enriched)
            except Exception as e:
                logger.warning("Auto-reply failed (non-fatal)", error=str(e))

        draft_strategy = "standard"
        if is_vip or priority >= 80:
            draft_strategy = "corporate_shield"
        elif state.is_meeting:
            draft_strategy = "meeting_dual"
        elif category in ("newsletter", "promotional", "spam"):
            draft_strategy = "none"

        if auto_reply_result:
            decision = f"Auto-reply sent (confidence: {auto_reply_result.get('confidence', 0):.0%})"
        elif draft_strategy == "corporate_shield":
            decision = "VIP sender — Corporate Shield Protocol for on-demand draft"
        elif draft_strategy == "meeting_dual":
            decision = "Meeting — dual accept/decline drafts on-demand"
        else:
            decision = f"Draft strategy: {draft_strategy}"

        return AgentResult(
            agent_name=self.name,
            output={
                "draft_strategy": draft_strategy,
                "auto_reply_eligible": auto_reply_eligible,
                "auto_reply_sent": auto_reply_result is not None,
                "auto_reply": auto_reply_result,
                "_decision": decision,
            },
            reasoning=self._build_reasoning(
                decision=decision,
                reason=f"Category: {category}, Priority: {priority}, VIP: {is_vip}",
                confidence=0.85,
            ),
        )
