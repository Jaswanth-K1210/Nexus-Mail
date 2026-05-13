"""
Nexus Mail — Agent Base Classes & Runtime Types

Production-grade base agent with:
- Structured output (AgentResult with reasoning traces)
- Automatic telemetry (token count, latency, retries)
- Retry-with-reflection on failure
- Tool integration interface
- Memory access interface

Inspired by LangGraph agent nodes, CrewAI agent definitions, and OpenAI Agents SDK.
"""

import time
import uuid
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

import structlog

logger = structlog.get_logger(__name__)


# ─── Agent Lifecycle States ──────────────────────────────────────────────────

class AgentStatus(str, Enum):
    IDLE = "idle"
    EXECUTING = "executing"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    SKIPPED = "skipped"


# ─── Reasoning Trace ─────────────────────────────────────────────────────────

class ReasoningStep(BaseModel):
    """A single step in the agent's chain-of-thought reasoning."""
    step: int
    thought: str
    action: str = ""
    observation: str = ""


class ReasoningTrace(BaseModel):
    """Complete reasoning trace for an agent execution."""
    agent: str
    decision: str
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)
    steps: list[ReasoningStep] = []
    reflection: Optional[str] = None


# ─── Tool Invocation Record ──────────────────────────────────────────────────

class ToolInvocation(BaseModel):
    """Record of a tool used during agent execution."""
    tool_name: str
    input_summary: str
    output_summary: str
    success: bool
    latency_ms: float
    error: Optional[str] = None


# ─── Agent Result ─────────────────────────────────────────────────────────────

class AgentResult(BaseModel):
    """
    Structured output from any agent execution.
    Every agent produces this — enabling unified telemetry, debugging, and orchestration.
    """
    # Identity
    agent_name: str
    agent_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    execution_id: str = ""

    # Output
    output: dict = {}
    status: AgentStatus = AgentStatus.SUCCESS

    # Reasoning
    reasoning: ReasoningTrace | None = None

    # Telemetry
    latency_ms: float = 0.0
    tokens_used: int = 0
    retry_count: int = 0
    tool_invocations: list[ToolInvocation] = []

    # Error handling
    error: Optional[str] = None
    fallback_used: bool = False


# ─── Base Agent ───────────────────────────────────────────────────────────────

class BaseAgent(ABC):
    """
    Abstract base class for all Nexus Mail agents.

    Every agent:
    1. Has a name and description
    2. Accepts a WorkflowState and produces an AgentResult
    3. Automatically tracks latency, tokens, retries
    4. Can access tools via self.tools
    5. Can access memory via self.memory
    6. Produces structured reasoning traces
    7. Supports retry-with-reflection on failure

    Subclasses implement _execute() with their domain logic.
    """

    name: str = "base_agent"
    description: str = "Base agent"
    max_retries: int = 2

    def __init__(self):
        self._tools: dict[str, Any] = {}
        self._memory: Any = None
        self._status: AgentStatus = AgentStatus.IDLE
        self._execution_id: str = ""

    # ─── Tool & Memory Injection ──────────────────────────────────────────

    def register_tool(self, name: str, tool: Any) -> None:
        """Register a tool for this agent to use."""
        self._tools[name] = tool

    def register_tools(self, tools: dict[str, Any]) -> None:
        """Register multiple tools at once."""
        self._tools.update(tools)

    def get_tool(self, name: str) -> Any:
        """Get a registered tool by name."""
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Agent '{self.name}' has no tool '{name}'. Available: {list(self._tools.keys())}")
        return tool

    def set_memory(self, memory: Any) -> None:
        """Inject the memory store."""
        self._memory = memory

    @property
    def memory(self) -> Any:
        return self._memory

    # ─── Public Execution Interface ───────────────────────────────────────

    async def run(self, state: "WorkflowState", execution_id: str = "") -> AgentResult:
        """
        Execute the agent with full telemetry wrapping.
        This is the public API — orchestrator calls this.

        Flow:
        1. Record start time
        2. Call _execute() (subclass logic)
        3. On failure: retry with reflection prompt
        4. Record telemetry
        5. Return AgentResult
        """
        self._execution_id = execution_id or str(uuid.uuid4())[:12]
        self._status = AgentStatus.EXECUTING
        start_time = time.perf_counter()
        last_error: str | None = None

        for attempt in range(1 + self.max_retries):
            try:
                if attempt > 0:
                    self._status = AgentStatus.RETRYING
                    logger.warning(
                        "Agent retrying with reflection",
                        agent=self.name,
                        attempt=attempt + 1,
                        last_error=last_error[:200] if last_error else "",
                    )

                # Execute the agent's domain logic
                result = await self._execute(state)

                # Ensure we have an AgentResult
                if not isinstance(result, AgentResult):
                    result = AgentResult(
                        agent_name=self.name,
                        output=result if isinstance(result, dict) else {"data": result},
                    )

                # Stamp telemetry
                result.execution_id = self._execution_id
                result.latency_ms = (time.perf_counter() - start_time) * 1000
                result.retry_count = attempt
                result.status = AgentStatus.SUCCESS
                self._status = AgentStatus.SUCCESS

                logger.info(
                    "Agent completed",
                    agent=self.name,
                    latency_ms=round(result.latency_ms, 1),
                    tokens=result.tokens_used,
                    retries=attempt,
                    confidence=result.reasoning.confidence if result.reasoning else None,
                )

                return result

            except Exception as e:
                last_error = str(e)
                logger.error(
                    "Agent execution failed",
                    agent=self.name,
                    attempt=attempt + 1,
                    error=last_error[:300],
                )

                if attempt >= self.max_retries:
                    self._status = AgentStatus.FAILED
                    return AgentResult(
                        agent_name=self.name,
                        execution_id=self._execution_id,
                        status=AgentStatus.FAILED,
                        error=last_error,
                        latency_ms=(time.perf_counter() - start_time) * 1000,
                        retry_count=attempt,
                        fallback_used=True,
                        reasoning=ReasoningTrace(
                            agent=self.name,
                            decision="Fallback to default",
                            reason=f"All {self.max_retries + 1} attempts failed: {last_error[:200]}",
                            confidence=0.0,
                        ),
                    )

        # Should not reach here
        self._status = AgentStatus.FAILED
        return AgentResult(
            agent_name=self.name,
            execution_id=self._execution_id,
            status=AgentStatus.FAILED,
            error="Unexpected execution path",
        )

    # ─── Subclass Interface ───────────────────────────────────────────────

    @abstractmethod
    async def _execute(self, state: "WorkflowState") -> AgentResult:
        """
        Implement the agent's domain logic.

        Must return an AgentResult with:
        - output: the agent's structured output dict
        - reasoning: a ReasoningTrace explaining decisions
        - tokens_used: estimated token count
        - tool_invocations: list of tools used

        Raise an exception to trigger retry-with-reflection.
        """
        ...

    # ─── Helpers ──────────────────────────────────────────────────────────

    def _build_reasoning(
        self,
        decision: str,
        reason: str,
        confidence: float,
        steps: list[dict] | None = None,
        reflection: str | None = None,
    ) -> ReasoningTrace:
        """Helper to build a ReasoningTrace."""
        reasoning_steps = []
        if steps:
            for i, s in enumerate(steps, 1):
                reasoning_steps.append(ReasoningStep(
                    step=i,
                    thought=s.get("thought", ""),
                    action=s.get("action", ""),
                    observation=s.get("observation", ""),
                ))

        return ReasoningTrace(
            agent=self.name,
            decision=decision,
            reason=reason,
            confidence=confidence,
            steps=reasoning_steps,
            reflection=reflection,
        )

    def _record_tool_use(
        self,
        tool_name: str,
        input_summary: str,
        output_summary: str,
        success: bool,
        latency_ms: float,
        error: str | None = None,
    ) -> ToolInvocation:
        """Helper to record a tool invocation."""
        return ToolInvocation(
            tool_name=tool_name,
            input_summary=input_summary,
            output_summary=output_summary,
            success=success,
            latency_ms=latency_ms,
            error=error,
        )
