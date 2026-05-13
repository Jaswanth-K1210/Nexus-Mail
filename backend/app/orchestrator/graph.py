"""
Nexus Mail — Orchestration Engine & State Graph

LangGraph-inspired stateful execution graph for multi-agent email processing.

Architecture:
- StateGraph with conditional routing
- Parallel execution for independent agents
- Retry branches with fallback
- Memory persistence at graph boundaries
- Human-in-the-loop checkpoints

Graph Structure:
    START → triage → [conditional]
                      ├─ if meeting → meeting → parallel(actions, security, summary)
                      ├─ if spam/auto-archive → persist (fast path)
                      └─ else → parallel(actions, security, summary)
    parallel_results → response → memory → persist → END
"""

import asyncio
from datetime import datetime, timezone

from app.agents.base import AgentResult, AgentStatus
from app.agents.state import WorkflowState, EmailContext, UserContext, ExecutionStatus
from app.agents.registry import get_agent_registry
from app.memory.store import get_memory_store
from app.telemetry.tracer import Tracer, metrics_collector, decision_logger
from app.tools.implementations import (
    GmailTool, CalendarTool, DraftTool, SearchTool, AnalyticsTool, ThreadContextTool
)

import structlog

logger = structlog.get_logger(__name__)


class EmailProcessingGraph:
    """
    LangGraph-inspired stateful execution graph for email processing.

    Nodes:
        triage    → TriageAgent (classification + priority + sender analysis)
        meeting   → MeetingAgent (calendar reasoning, conditional)
        actions   → ActionAgent (task extraction)
        security  → SecurityAgent (risk detection)
        summary   → Summarization (existing task, run inline)
        response  → ResponseAgent (draft strategy + auto-reply)
        memory    → MemoryAgent (persist to long-term memory)
        persist   → Database persistence node (non-agent)

    Edges:
        START → triage
        triage → conditional_router
        conditional_router:
            if is_meeting → meeting
            if spam/low_priority → fast_path_persist
            else → parallel(actions, security, summary)
        meeting → parallel(actions, security, summary)
        parallel → response
        response → memory
        memory → persist
        persist → END
    """

    def __init__(self):
        self._setup_agents()
        self._setup_tools()
        self._setup_memory()

    def _setup_agents(self):
        """Register all agents in the registry."""
        from app.agents.triage_agent import TriageAgent
        from app.agents.meeting_agent import MeetingAgent
        from app.agents.action_agent import ActionAgent
        from app.agents.security_agent import SecurityAgent
        from app.agents.response_agent import ResponseAgent
        from app.agents.memory_agent import MemoryAgent

        registry = get_agent_registry()
        registry.register_all([
            TriageAgent,
            MeetingAgent,
            ActionAgent,
            SecurityAgent,
            ResponseAgent,
            MemoryAgent,
        ])

    def _setup_tools(self):
        """Create and inject tools into agents."""
        tools = {
            "gmail": GmailTool(),
            "calendar": CalendarTool(),
            "draft": DraftTool(),
            "search": SearchTool(),
            "analytics": AnalyticsTool(),
            "thread_context": ThreadContextTool(),
        }
        registry = get_agent_registry()
        registry.inject_tools(tools)

    def _setup_memory(self):
        """Inject memory store into agents."""
        memory = get_memory_store()
        registry = get_agent_registry()
        registry.inject_memory(memory)

    async def execute(self, email_doc: dict, user_id: str) -> dict:
        """
        Execute the full email processing graph.

        This is the main entry point — called by ProcessingPipeline.
        Returns the combined results from all agents.
        """
        from app.ai_worker.sanitizer import sanitize_email_body
        from bson import ObjectId
        from app.core.database import get_database

        db = get_database()
        registry = get_agent_registry()
        memory = get_memory_store()

        # ─── Initialize State ────────────────────────────────────────────
        sanitized_body = sanitize_email_body(
            body_text=email_doc.get("body_text", ""),
            body_html=email_doc.get("body_html", ""),
        )

        email_ctx = EmailContext.from_email_doc(email_doc, sanitized_body)

        # Load user context
        user_doc = await db.users.find_one(
            {"_id": ObjectId(user_id)},
            {"tone_profile": 1, "user_context": 1},
        )
        user_persona = ""
        user_role = None
        if user_doc:
            if user_doc.get("tone_profile"):
                user_persona = user_doc["tone_profile"].get("professional_persona", "")
            if user_doc.get("user_context"):
                user_role = user_doc["user_context"].get("role_key")

        user_ctx = UserContext(
            user_id=user_id,
            user_persona=user_persona,
            user_role=user_role,
            tone_profile=user_doc.get("tone_profile") if user_doc else None,
        )

        state = WorkflowState(
            email=email_ctx,
            user=user_ctx,
            raw_email_doc=email_doc,
        )
        state.status = ExecutionStatus.RUNNING

        # Pre-load memory context
        state.memory_context = await memory.load_context_for_email(
            user_id, email_ctx.sender_email, email_ctx.thread_id
        )

        # Initialize tracer
        tracer = Tracer(user_id=user_id, email_id=email_ctx.email_id)

        # ─── Node 1: Triage ───────────────────────────────────────────────
        with tracer.span("triage_agent", kind="agent") as span:
            triage = registry.get("triage_agent")
            triage_result = await triage.run(state, execution_id=state.execution_id)
            state.record_agent_result("triage_agent", triage_result)
            span.attributes["category"] = state.category
            span.attributes["priority"] = state.priority_score
            span.attributes["is_meeting"] = state.is_meeting
            tracer.add_routing("triage_agent")
            tracer.add_tokens(triage_result.tokens_used)

        # Log triage decision
        await decision_logger.log_decision(
            user_id=user_id,
            email_id=email_ctx.email_id,
            agent_name="triage_agent",
            decision=triage_result.reasoning.decision if triage_result.reasoning else "",
            reason=triage_result.reasoning.reason if triage_result.reasoning else "",
            confidence=triage_result.reasoning.confidence if triage_result.reasoning else 0,
        )

        # ─── Conditional Router ───────────────────────────────────────────
        fast_path = state.category in ("spam",) and state.suggested_action == "AUTO-ARCHIVE"

        if fast_path:
            state.add_routing_decision("triage_agent", "persist", "Spam/auto-archive fast path")
            tracer.add_routing("fast_path_persist")
        else:
            # ─── Node 2 (conditional): Meeting ────────────────────────────
            if state.is_meeting:
                state.add_routing_decision("triage_agent", "meeting_agent", "Meeting invitation detected")
                with tracer.span("meeting_agent", kind="agent") as span:
                    meeting = registry.get("meeting_agent")
                    meeting_result = await meeting.run(state, execution_id=state.execution_id)
                    state.record_agent_result("meeting_agent", meeting_result)
                    span.attributes["availability"] = meeting_result.output.get("availability")
                    tracer.add_routing("meeting_agent")
                    tracer.add_tokens(meeting_result.tokens_used)
            else:
                state.add_routing_decision("triage_agent", "parallel_agents", "Standard email processing")

            # ─── Nodes 3-5 (parallel): Actions + Security + Summary ───────
            with tracer.span("parallel_agents", kind="agent"):
                async def run_actions():
                    agent = registry.get("action_agent")
                    return await agent.run(state, execution_id=state.execution_id)

                async def run_security():
                    agent = registry.get("security_agent")
                    return await agent.run(state, execution_id=state.execution_id)

                async def run_summary():
                    from app.ai_worker.tasks.summarise import summarise_email
                    return await summarise_email(
                        subject=email_ctx.subject,
                        body=email_ctx.body,
                        sender=f"{email_ctx.sender_name} <{email_ctx.sender_email}>",
                        is_meeting=state.is_meeting,
                    )

                results = await asyncio.gather(
                    run_actions(), run_security(), run_summary(),
                    return_exceptions=True,
                )

                action_result, security_result, summary_result = results

                if isinstance(action_result, AgentResult):
                    state.record_agent_result("action_agent", action_result)
                    tracer.add_tokens(action_result.tokens_used)
                elif isinstance(action_result, Exception):
                    logger.error("Action agent failed", error=str(action_result))

                if isinstance(security_result, AgentResult):
                    state.record_agent_result("security_agent", security_result)
                    tracer.add_tokens(security_result.tokens_used)
                elif isinstance(security_result, Exception):
                    logger.error("Security agent failed", error=str(security_result))

                if isinstance(summary_result, dict):
                    state.agent_results["summarizer"] = summary_result
                elif isinstance(summary_result, Exception):
                    logger.error("Summarization failed", error=str(summary_result))
                    summary_result = {"summary": "Summary generation failed", "key_topic": "Unknown"}
                    state.agent_results["summarizer"] = summary_result

                tracer.add_routing("parallel_agents")

            # ─── Node 6: Response ─────────────────────────────────────────
            with tracer.span("response_agent", kind="agent"):
                response = registry.get("response_agent")
                response_result = await response.run(state, execution_id=state.execution_id)
                state.record_agent_result("response_agent", response_result)
                tracer.add_routing("response_agent")

            # ─── Node 7: Memory ──────────────────────────────────────────
            with tracer.span("memory_agent", kind="agent"):
                mem_agent = registry.get("memory_agent")
                mem_result = await mem_agent.run(state, execution_id=state.execution_id)
                state.record_agent_result("memory_agent", mem_result)
                tracer.add_routing("memory_agent")

        # ─── Finalize ─────────────────────────────────────────────────────
        state.status = ExecutionStatus.COMPLETED
        state.completed_at = datetime.now(timezone.utc)

        # Record metrics
        await metrics_collector.record_agent_execution(
            user_id=user_id,
            agent_name="orchestrator",
            latency_ms=state.total_latency_ms,
            tokens_used=state.total_tokens,
            success=True,
        )

        # Persist trace
        trace = tracer.finalize("completed")
        await tracer.persist(trace)

        # ─── Build combined results (backward compatible) ─────────────────
        triage_out = state.get_agent_output("triage_agent")
        classification = triage_out.get("classification", {})
        summary_out = state.agent_results.get("summarizer", {})
        action_out = state.get_agent_output("action_agent")
        security_out = state.get_agent_output("security_agent")
        meeting_out = state.get_agent_output("meeting_agent")
        response_out = state.get_agent_output("response_agent")

        combined = {
            "email_id": email_ctx.email_id,
            "execution_id": state.execution_id,
            "classification": classification,
            "summary": summary_out,
            "actions": action_out.get("actions", {}),
            "risks": security_out.get("risks", {}),
            "priority_score": state.priority_score,
            "meeting_intelligence": meeting_out.get("meeting_result") if meeting_out else None,
            "auto_reply": response_out.get("auto_reply") if response_out else None,
            "tasks_completed": list(state.agent_results.keys()),
            # Agent reasoning (new — for frontend)
            "agent_reasoning": state.agent_reasoning,
            "execution_timeline": [e.model_dump() for e in state.timeline],
            "total_tokens": state.total_tokens,
            "total_latency_ms": round(state.total_latency_ms, 1),
            "trace_id": tracer.trace_id,
        }

        return combined


# ─── Singleton ────────────────────────────────────────────────────────────────

_graph: EmailProcessingGraph | None = None


def get_email_processing_graph() -> EmailProcessingGraph:
    """Get or create the global email processing graph singleton."""
    global _graph
    if _graph is None:
        _graph = EmailProcessingGraph()
    return _graph
