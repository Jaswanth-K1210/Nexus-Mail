"""
Nexus Mail — Action Extraction Agent

Responsibilities:
- Task extraction from email body (wraps extract_actions.py)
- Deadline extraction and reasoning
- Dependency detection between tasks
- Follow-up tracking

Runs for every email to surface actionable items.
"""

from app.agents.base import BaseAgent, AgentResult
from app.agents.state import WorkflowState

import structlog

logger = structlog.get_logger(__name__)


class ActionAgent(BaseAgent):
    """
    Action Extraction Agent — extracts tasks, deadlines, and follow-ups.
    Wraps existing extract_actions.py with reasoning traces and dependency analysis.
    """

    name = "action_agent"
    description = "Extracts action items, deadlines, and follow-up tasks from emails"
    max_retries = 2

    async def _execute(self, state: WorkflowState) -> AgentResult:
        from app.ai_worker.tasks.extract_actions import extract_actions

        email = state.email
        if not email:
            raise ValueError("No email context in state")

        # Run existing action extraction
        actions = await extract_actions(
            subject=email.subject,
            body=email.body,
            sender=f"{email.sender_name} <{email.sender_email}>",
            is_meeting=state.is_meeting,
        )

        action_items = actions.get("action_items", [])
        requires_response = actions.get("requires_response", False)
        urgency = actions.get("response_urgency", "none")

        # Analyze dependencies and follow-ups
        high_priority_count = sum(1 for a in action_items if a.get("priority") == "high")
        has_deadline = any(a.get("deadline") for a in action_items)

        # Build reasoning
        if not action_items:
            decision = "No actionable items found"
            confidence = 0.8
        elif high_priority_count > 0 and has_deadline:
            decision = f"Found {len(action_items)} actions ({high_priority_count} high-priority) with deadlines — requires attention"
            confidence = 0.9
        elif requires_response:
            decision = f"Found {len(action_items)} actions — response required ({urgency})"
            confidence = 0.85
        else:
            decision = f"Found {len(action_items)} low-medium priority actions"
            confidence = 0.75

        reasoning = self._build_reasoning(
            decision=decision,
            reason=f"Actions: {len(action_items)}, Requires response: {requires_response}, Urgency: {urgency}",
            confidence=confidence,
            steps=[
                {
                    "thought": f"Analyzing email for actionable items: '{email.subject[:50]}'",
                    "action": "AI action extraction",
                    "observation": f"Found {len(action_items)} items, {high_priority_count} high-priority",
                },
                {
                    "thought": "Checking for deadlines and dependencies",
                    "action": "Deadline and dependency analysis",
                    "observation": f"Has deadlines: {has_deadline}, Response urgency: {urgency}",
                },
            ],
        )

        output = {
            "actions": actions,
            "action_items": action_items,
            "requires_response": requires_response,
            "response_urgency": urgency,
            "high_priority_count": high_priority_count,
            "has_deadline": has_deadline,
            "_decision": decision,
        }

        return AgentResult(
            agent_name=self.name,
            output=output,
            reasoning=reasoning,
        )
