"""
Nexus Mail — Telemetry: Execution Tracing

OpenTelemetry-compatible span-based tracing for agent executions.
Captures agent runs, tool invocations, memory lookups, and routing decisions.
Stored in MongoDB for dashboard visualization and debugging.
"""

import time
import uuid
from datetime import datetime, timezone
from typing import Optional, Any

from pydantic import BaseModel, Field

import structlog

logger = structlog.get_logger(__name__)


# ─── Trace Span ───────────────────────────────────────────────────────────────

class TraceSpan(BaseModel):
    """A single span within an execution trace (OpenTelemetry-compatible structure)."""
    span_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    parent_span_id: Optional[str] = None
    name: str
    kind: str = "agent"  # agent | tool | memory | routing | checkpoint
    status: str = "ok"   # ok | error
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None
    duration_ms: float = 0.0
    attributes: dict = {}
    events: list[dict] = []
    error: Optional[str] = None


# ─── Execution Trace ──────────────────────────────────────────────────────────

class ExecutionTrace(BaseModel):
    """
    Complete execution trace for a single email processing workflow.
    Contains all spans from orchestrator → agents → tools → memory.
    """
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_name: str = "email_processing"
    user_id: str = ""
    email_id: str = ""
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None
    total_duration_ms: float = 0.0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    status: str = "running"  # running | completed | failed
    spans: list[TraceSpan] = []
    routing_path: list[str] = []  # ordered list of nodes executed
    metadata: dict = {}


# ─── Trace Context Manager ───────────────────────────────────────────────────

class Tracer:
    """
    Production-grade execution tracer.

    Usage:
        tracer = Tracer(user_id="...", email_id="...")

        with tracer.span("triage_agent", kind="agent") as span:
            result = await triage_agent.run(state)
            span.attributes["category"] = result.output.get("category")
            span.attributes["tokens"] = result.tokens_used

        trace = tracer.finalize()
        await tracer.persist(trace)
    """

    def __init__(self, user_id: str = "", email_id: str = ""):
        self.trace = ExecutionTrace(user_id=user_id, email_id=email_id)
        self._span_stack: list[TraceSpan] = []

    @property
    def trace_id(self) -> str:
        return self.trace.trace_id

    def span(self, name: str, kind: str = "agent") -> "SpanContext":
        """Create a new span context manager."""
        parent_id = self._span_stack[-1].span_id if self._span_stack else None
        span = TraceSpan(
            name=name,
            kind=kind,
            parent_span_id=parent_id,
        )
        return SpanContext(self, span)

    def _start_span(self, span: TraceSpan) -> None:
        """Called when entering a span context."""
        span.started_at = datetime.now(timezone.utc)
        self._span_stack.append(span)

    def _end_span(self, span: TraceSpan, error: str | None = None) -> None:
        """Called when exiting a span context."""
        span.ended_at = datetime.now(timezone.utc)
        span.duration_ms = (span.ended_at - span.started_at).total_seconds() * 1000
        span.status = "error" if error else "ok"
        span.error = error
        self.trace.spans.append(span)
        if self._span_stack and self._span_stack[-1].span_id == span.span_id:
            self._span_stack.pop()

    def add_routing(self, node: str) -> None:
        """Record a node in the routing path."""
        self.trace.routing_path.append(node)

    def add_tokens(self, tokens: int) -> None:
        """Add to total token count."""
        self.trace.total_tokens += tokens

    def finalize(self, status: str = "completed") -> ExecutionTrace:
        """Finalize the trace with completion status."""
        self.trace.ended_at = datetime.now(timezone.utc)
        self.trace.total_duration_ms = (
            self.trace.ended_at - self.trace.started_at
        ).total_seconds() * 1000
        self.trace.status = status
        return self.trace

    async def persist(self, trace: ExecutionTrace | None = None) -> str:
        """Store the trace in MongoDB for dashboard access."""
        trace = trace or self.trace
        try:
            from app.core.database import get_database
            db = get_database()
            doc = trace.model_dump()
            result = await db.execution_traces.insert_one(doc)
            logger.debug(
                "Trace persisted",
                trace_id=trace.trace_id,
                duration_ms=round(trace.total_duration_ms, 1),
                spans=len(trace.spans),
            )
            return str(result.inserted_id)
        except Exception as e:
            logger.warning("Failed to persist trace", error=str(e))
            return ""


# ─── Span Context Manager ────────────────────────────────────────────────────

class SpanContext:
    """Context manager for a trace span."""

    def __init__(self, tracer: Tracer, span: TraceSpan):
        self._tracer = tracer
        self._span = span

    def __enter__(self) -> TraceSpan:
        self._tracer._start_span(self._span)
        return self._span

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        error = str(exc_val) if exc_val else None
        self._tracer._end_span(self._span, error=error)
        return False  # Don't suppress exceptions


# ─── Metrics Collector ────────────────────────────────────────────────────────

class MetricsCollector:
    """
    Collects and aggregates AI system metrics.
    Stores daily metrics in MongoDB for dashboard visualization.
    """

    async def record_agent_execution(
        self,
        user_id: str,
        agent_name: str,
        latency_ms: float,
        tokens_used: int,
        success: bool,
        retries: int = 0,
    ) -> None:
        """Record metrics for a single agent execution."""
        try:
            from app.core.database import get_database
            db = get_database()

            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            await db.agent_metrics.update_one(
                {"date": today, "agent": agent_name},
                {
                    "$inc": {
                        "total_executions": 1,
                        "total_tokens": tokens_used,
                        "total_retries": retries,
                        "success_count": 1 if success else 0,
                        "failure_count": 0 if success else 1,
                    },
                    "$push": {
                        "latencies": {"$each": [latency_ms], "$slice": -100},
                    },
                    "$set": {
                        "last_execution": datetime.now(timezone.utc),
                    },
                },
                upsert=True,
            )
        except Exception as e:
            logger.warning("Failed to record metrics", error=str(e))

    async def record_tool_execution(
        self,
        tool_name: str,
        latency_ms: float,
        success: bool,
    ) -> None:
        """Record metrics for a tool invocation."""
        try:
            from app.core.database import get_database
            db = get_database()

            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            await db.tool_metrics.update_one(
                {"date": today, "tool": tool_name},
                {
                    "$inc": {
                        "total_invocations": 1,
                        "success_count": 1 if success else 0,
                        "failure_count": 0 if success else 1,
                    },
                    "$push": {
                        "latencies": {"$each": [latency_ms], "$slice": -100},
                    },
                },
                upsert=True,
            )
        except Exception as e:
            logger.warning("Failed to record tool metrics", error=str(e))

    async def get_agent_metrics(self, days: int = 7) -> list[dict]:
        """Get agent metrics for the last N days."""
        try:
            from app.core.database import get_database
            from datetime import timedelta
            db = get_database()

            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

            cursor = db.agent_metrics.find(
                {"date": {"$gte": cutoff}},
                {"_id": 0},
            ).sort("date", -1)

            return await cursor.to_list(length=100)
        except Exception as e:
            logger.warning("Failed to get metrics", error=str(e))
            return []


# ─── Decision Logger ──────────────────────────────────────────────────────────

class DecisionLogger:
    """
    Logs every agent decision with reasoning for audit, debugging, and self-improvement.
    Enables "why did the AI do this?" debugging.
    """

    async def log_decision(
        self,
        user_id: str,
        email_id: str,
        agent_name: str,
        decision: str,
        reason: str,
        confidence: float,
        metadata: dict | None = None,
    ) -> None:
        """Log a single agent decision."""
        try:
            from app.core.database import get_database
            db = get_database()

            await db.agent_decisions.insert_one({
                "user_id": user_id,
                "email_id": email_id,
                "agent": agent_name,
                "decision": decision,
                "reason": reason,
                "confidence": confidence,
                "metadata": metadata or {},
                "timestamp": datetime.now(timezone.utc),
            })
        except Exception as e:
            logger.warning("Failed to log decision", error=str(e))

    async def get_decisions(
        self,
        user_id: str,
        email_id: str | None = None,
        agent: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Retrieve logged decisions for debugging."""
        try:
            from app.core.database import get_database
            db = get_database()

            query: dict = {"user_id": user_id}
            if email_id:
                query["email_id"] = email_id
            if agent:
                query["agent"] = agent

            cursor = db.agent_decisions.find(
                query, {"_id": 0}
            ).sort("timestamp", -1).limit(limit)

            return await cursor.to_list(length=limit)
        except Exception as e:
            logger.warning("Failed to get decisions", error=str(e))
            return []


# ─── Singletons ───────────────────────────────────────────────────────────────

metrics_collector = MetricsCollector()
decision_logger = DecisionLogger()
