"""
Nexus Mail — Meeting Intelligence Agent

Responsibilities:
- Calendar reasoning (wraps existing meeting_intelligence.py)
- Scheduling conflict detection
- Attendee extraction and context
- Time prioritization
- Meeting intent understanding

Only executes when TriageAgent flags is_meeting_invitation=True.
"""

from app.agents.base import BaseAgent, AgentResult
from app.agents.state import WorkflowState

import structlog

logger = structlog.get_logger(__name__)


class MeetingAgent(BaseAgent):
    """
    Meeting Intelligence Agent — conditional node in the execution graph.

    Extracts meeting data, checks calendar availability, detects conflicts,
    and creates meeting alerts. Only runs for meeting invitations.
    """

    name = "meeting_agent"
    description = "Processes meeting invitations with calendar reasoning and conflict detection"
    max_retries = 2

    async def _execute(self, state: WorkflowState) -> AgentResult:
        from app.ai_worker.tasks.meeting_intelligence import process_meeting_invitation
        from app.services.auth_service import AuthService

        email = state.email
        if not email:
            raise ValueError("No email context in state")

        if not state.is_meeting:
            return AgentResult(
                agent_name=self.name,
                output={"skipped": True, "reason": "Not a meeting invitation"},
                reasoning=self._build_reasoning(
                    decision="Skipped — not a meeting invitation",
                    reason="TriageAgent did not flag this as a meeting",
                    confidence=1.0,
                ),
            )

        # Get credentials for calendar access
        auth = AuthService()
        credentials = await auth.get_user_credentials(email.user_id)

        # Run the existing meeting intelligence pipeline
        meeting_result = await process_meeting_invitation(
            email_id=email.email_id,
            user_id=email.user_id,
            email_body=email.body,
            sender_name=email.sender_name,
            sender_email=email.sender_email,
            subject=email.subject,
            thread_id=email.thread_id,
            credentials=credentials,
        )

        if not meeting_result:
            return AgentResult(
                agent_name=self.name,
                output={"skipped": True, "reason": "Meeting confidence below threshold"},
                reasoning=self._build_reasoning(
                    decision="Meeting data extraction failed confidence check",
                    reason="The meeting detection confidence was below the threshold — likely not a real meeting invite",
                    confidence=0.3,
                ),
            )

        # Build reasoning trace
        availability = meeting_result.get("availability", "unknown")
        proposed_dt = meeting_result.get("proposed_datetime", "")

        reasoning_steps = [
            {
                "thought": f"Extracting meeting data from email: '{email.subject[:50]}'",
                "action": "AI meeting data extraction",
                "observation": f"Proposed time: {proposed_dt}, Duration: {meeting_result.get('duration_minutes', 60)}min",
            },
            {
                "thought": "Checking Google Calendar for conflicts",
                "action": "Calendar availability check",
                "observation": f"Availability: {availability}",
            },
        ]

        if availability == "busy":
            decision = f"CONFLICT detected — user is busy at {proposed_dt}"
            confidence = 0.9
        elif availability == "partial":
            decision = f"Partial conflict — nearby events at {proposed_dt}"
            confidence = 0.75
        else:
            decision = f"Calendar is free at {proposed_dt} — no conflicts"
            confidence = 0.95

        reasoning = self._build_reasoning(
            decision=decision,
            reason=f"Meeting from {email.sender_name}, availability: {availability}",
            confidence=confidence,
            steps=reasoning_steps,
        )

        output = {
            "meeting_result": meeting_result,
            "availability": availability,
            "proposed_datetime": proposed_dt,
            "duration_minutes": meeting_result.get("duration_minutes", 60),
            "alert_id": meeting_result.get("alert_id", ""),
            "_decision": decision,
        }

        return AgentResult(
            agent_name=self.name,
            output=output,
            reasoning=reasoning,
        )
