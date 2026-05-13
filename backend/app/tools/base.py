"""
Nexus Mail — Tool Base Classes

Structured, traceable tool interfaces for agent use.
Every external integration (Gmail, Calendar, DB queries) is wrapped in a tool
with structured I/O, retries, latency tracking, and tracing.

Inspired by LangChain tools, OpenAI function calling, and MCP tool protocol.
"""

import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Optional

from pydantic import BaseModel, Field

import structlog

logger = structlog.get_logger(__name__)


# ─── Tool Result ──────────────────────────────────────────────────────────────

class ToolResult(BaseModel):
    """Structured output from any tool execution."""
    tool_name: str
    invocation_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    output: Any = None
    success: bool = True
    latency_ms: float = 0.0
    tokens_used: int = 0
    error: Optional[str] = None
    metadata: dict = {}


# ─── Base Tool ────────────────────────────────────────────────────────────────

class BaseTool(ABC):
    """
    Abstract base class for all tools available to agents.

    Every tool:
    1. Has a name and description
    2. Defines input/output schemas
    3. Automatically tracks latency and errors
    4. Supports retries with backoff
    5. Produces structured ToolResult
    """

    name: str = "base_tool"
    description: str = "Base tool"
    max_retries: int = 2

    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with automatic telemetry and retry.
        This is the public API — agents call this.
        """
        start_time = time.perf_counter()
        last_error: str | None = None

        for attempt in range(1 + self.max_retries):
            try:
                result = await self._run(**kwargs)

                latency = (time.perf_counter() - start_time) * 1000

                if isinstance(result, ToolResult):
                    result.latency_ms = latency
                    return result

                return ToolResult(
                    tool_name=self.name,
                    output=result,
                    success=True,
                    latency_ms=latency,
                )

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    "Tool execution failed",
                    tool=self.name,
                    attempt=attempt + 1,
                    error=last_error[:200],
                )

                if attempt >= self.max_retries:
                    return ToolResult(
                        tool_name=self.name,
                        output=None,
                        success=False,
                        latency_ms=(time.perf_counter() - start_time) * 1000,
                        error=last_error,
                    )

                # Brief backoff before retry
                import asyncio
                await asyncio.sleep(0.5 * (attempt + 1))

        return ToolResult(
            tool_name=self.name,
            success=False,
            error="Max retries exceeded",
        )

    @abstractmethod
    async def _run(self, **kwargs) -> Any:
        """Implement the tool's core logic. Raise on failure to trigger retry."""
        ...

    def get_schema(self) -> dict:
        """Return the tool's input/output schema for agent planning."""
        return {
            "name": self.name,
            "description": self.description,
        }
