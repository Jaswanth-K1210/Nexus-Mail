"""
Nexus Mail — Workflow State Definition

The shared state object passed through the agent execution graph.
Inspired by LangGraph's StateGraph state schema.

Every agent reads from and writes to this state.
The orchestrator manages state transitions and snapshots.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ─── Execution Status ─────────────────────────────────────────────────────────

class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    AWAITING_HUMAN = "awaiting_human"


# ─── Email Context ────────────────────────────────────────────────────────────

class EmailContext(BaseModel):
    """Normalized email data extracted from the raw MongoDB document."""
    email_id: str
    user_id: str
    gmail_id: str = ""
    thread_id: str = ""
    subject: str = ""
    sender_name: str = ""
    sender_email: str = ""
    body: str = ""          # sanitized body (post-processing)
    body_html: str = ""
    snippet: str = ""
    received_at: Optional[datetime] = None
    labels: list[str] = []
    has_ics: bool = False
    is_read: bool = False

    @classmethod
    def from_email_doc(cls, email_doc: dict, sanitized_body: str = "") -> "EmailContext":
        """Create from a MongoDB email document."""
        return cls(
            email_id=str(email_doc.get("_id", "")),
            user_id=email_doc.get("user_id", ""),
            gmail_id=email_doc.get("gmail_id", ""),
            thread_id=email_doc.get("thread_id", ""),
            subject=email_doc.get("subject", ""),
            sender_name=email_doc.get("sender_name", ""),
            sender_email=email_doc.get("sender_email", ""),
            body=sanitized_body or email_doc.get("body_text", ""),
            body_html=email_doc.get("body_html", ""),
            snippet=email_doc.get("snippet", ""),
            received_at=email_doc.get("received_at"),
            labels=email_doc.get("labels", []),
            has_ics=False,  # TODO: detect .ics attachments
            is_read=email_doc.get("is_read", False),
        )


# ─── User Context ─────────────────────────────────────────────────────────────

class UserContext(BaseModel):
    """User-specific context loaded at workflow start."""
    user_id: str
    user_persona: str = ""
    user_role: Optional[str] = None
    tone_profile: Optional[dict] = None
    auto_reply_enabled: bool = False


# ─── Routing Decision ─────────────────────────────────────────────────────────

class RoutingDecision(BaseModel):
    """Record of a routing decision made by the orchestrator."""
    from_node: str
    to_node: str
    reason: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ─── Execution Timeline Entry ─────────────────────────────────────────────────

class TimelineEntry(BaseModel):
    """A single entry in the execution timeline."""
    agent: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    latency_ms: float = 0.0
    tokens_used: int = 0
    confidence: Optional[float] = None
    decision: str = ""
    error: Optional[str] = None


# ─── Human-in-the-Loop Checkpoint ─────────────────────────────────────────────

class Checkpoint(BaseModel):
    """A pending human approval checkpoint."""
    checkpoint_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent: str
    action: str
    reason: str
    requires_approval: bool = True
    approved: Optional[bool] = None
    approved_at: Optional[datetime] = None


# ─── Workflow State ────────────────────────────────────────────────────────────

class WorkflowState(BaseModel):
    """
    The shared state object passed through the entire agent execution graph.

    This is the "single source of truth" during email processing.
    Every agent reads from and writes to specific fields.
    The orchestrator manages transitions and creates snapshots.

    Inspired by LangGraph's TypedDict state with channels.
    """

    # ─── Identity ─────────────────────────────────────────────────────────
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_name: str = "email_processing"
    status: ExecutionStatus = ExecutionStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    # ─── Input Context ────────────────────────────────────────────────────
    email: Optional[EmailContext] = None
    user: Optional[UserContext] = None
    raw_email_doc: dict = {}      # Original MongoDB document (for fallback)

    # ─── Agent Results (accumulated during execution) ─────────────────────
    agent_results: dict[str, dict] = {}    # agent_name → output dict
    agent_reasoning: dict[str, dict] = {}  # agent_name → reasoning trace

    # ─── Routing ──────────────────────────────────────────────────────────
    current_node: str = ""
    routing_decisions: list[RoutingDecision] = []

    # ─── Classification Results (set by TriageAgent) ──────────────────────
    category: Optional[str] = None
    severity: Optional[int] = None
    suggested_action: Optional[str] = None
    is_meeting: bool = False
    priority_score: int = 0

    # ─── Memory Context (loaded before agent execution) ───────────────────
    memory_context: dict = {}     # Pre-loaded memory for agents to use
    sender_profile: dict = {}     # Sender intelligence data

    # ─── Execution Timeline ───────────────────────────────────────────────
    timeline: list[TimelineEntry] = []
    total_tokens: int = 0
    total_latency_ms: float = 0.0

    # ─── Checkpoints ──────────────────────────────────────────────────────
    checkpoints: list[Checkpoint] = []
    requires_human_approval: bool = False

    # ─── Error Tracking ───────────────────────────────────────────────────
    errors: list[dict] = []

    # ─── Methods ──────────────────────────────────────────────────────────

    def record_agent_result(self, agent_name: str, result: Any) -> None:
        """Record an agent's output in the shared state."""
        from app.agents.base import AgentResult
        if isinstance(result, AgentResult):
            self.agent_results[agent_name] = result.output
            if result.reasoning:
                self.agent_reasoning[agent_name] = result.reasoning.model_dump()
            self.total_tokens += result.tokens_used
            self.total_latency_ms += result.latency_ms

            # Add to timeline
            self.timeline.append(TimelineEntry(
                agent=agent_name,
                status=result.status.value,
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                latency_ms=result.latency_ms,
                tokens_used=result.tokens_used,
                confidence=result.reasoning.confidence if result.reasoning else None,
                decision=result.reasoning.decision if result.reasoning else "",
                error=result.error,
            ))

            if result.error:
                self.errors.append({
                    "agent": agent_name,
                    "error": result.error,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
        else:
            self.agent_results[agent_name] = result if isinstance(result, dict) else {"data": result}

    def add_routing_decision(self, from_node: str, to_node: str, reason: str) -> None:
        """Record a routing decision."""
        self.routing_decisions.append(RoutingDecision(
            from_node=from_node,
            to_node=to_node,
            reason=reason,
        ))

    def get_agent_output(self, agent_name: str) -> dict:
        """Get a specific agent's output."""
        return self.agent_results.get(agent_name, {})

    def snapshot(self) -> dict:
        """Create a serializable snapshot of the current state for debugging."""
        return {
            "execution_id": self.execution_id,
            "status": self.status.value,
            "email_id": self.email.email_id if self.email else None,
            "current_node": self.current_node,
            "category": self.category,
            "is_meeting": self.is_meeting,
            "priority_score": self.priority_score,
            "agents_completed": list(self.agent_results.keys()),
            "total_tokens": self.total_tokens,
            "total_latency_ms": round(self.total_latency_ms, 1),
            "errors": len(self.errors),
            "timeline_entries": len(self.timeline),
        }
