"""
Nexus Mail — Communication Memory Agent

Responsibilities:
- Persist sender relationship data after processing
- Store agent decision episodes for future recall
- Update thread summaries for conversation continuity
- Track unresolved tasks and follow-ups

Runs as the final agent in the execution graph.
"""

from app.agents.base import BaseAgent, AgentResult
from app.agents.state import WorkflowState
import structlog

logger = structlog.get_logger(__name__)


class MemoryAgent(BaseAgent):
    name = "memory_agent"
    description = "Persists workflow results into long-term memory for future agent decisions"
    max_retries = 1

    async def _execute(self, state: WorkflowState) -> AgentResult:
        email = state.email
        if not email:
            raise ValueError("No email context in state")

        persisted_items = []
        memory = self._memory

        if not memory:
            return AgentResult(
                agent_name=self.name,
                output={"persisted": False, "reason": "No memory store available"},
                reasoning=self._build_reasoning(
                    decision="Skipped — no memory store injected",
                    reason="Memory store not configured",
                    confidence=1.0,
                ),
            )

        # Persist all workflow results
        try:
            summary = ""
            triage_output = state.get_agent_output("triage_agent")
            if triage_output:
                summary = f"Category: {triage_output.get('category')}, Priority: {triage_output.get('priority_score')}"

            await memory.persist_workflow_results(
                user_id=email.user_id,
                email_id=email.email_id,
                sender_email=email.sender_email,
                thread_id=email.thread_id,
                agent_results=state.agent_results,
                workflow_summary=summary,
            )
            persisted_items.append("workflow_results")
        except Exception as e:
            logger.warning("Workflow persistence failed", error=str(e))

        # Store unresolved action items for follow-up tracking
        action_output = state.get_agent_output("action_agent")
        if action_output:
            action_items = action_output.get("action_items", [])
            high_priority = [a for a in action_items if a.get("priority") == "high"]
            if high_priority:
                try:
                    await memory.long_term.store_sender_memory(
                        user_id=email.user_id,
                        sender_email=email.sender_email,
                        memory_type="unresolved_tasks",
                        data={
                            "email_id": email.email_id,
                            "tasks": [a.get("action", "") for a in high_priority],
                            "urgency": action_output.get("response_urgency", "none"),
                        },
                    )
                    persisted_items.append("unresolved_tasks")
                except Exception as e:
                    logger.warning("Task persistence failed", error=str(e))

        decision = f"Persisted {len(persisted_items)} memory items: {', '.join(persisted_items)}"

        return AgentResult(
            agent_name=self.name,
            output={"persisted": True, "items": persisted_items},
            reasoning=self._build_reasoning(
                decision=decision,
                reason=f"Stored results for sender {email.sender_email} in long-term memory",
                confidence=0.95,
            ),
        )
