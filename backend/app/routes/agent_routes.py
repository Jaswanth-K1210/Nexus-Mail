"""
Nexus Mail — Agent System API Routes

Endpoints for:
- Agent telemetry and metrics
- Execution trace viewer
- Decision log access
- Memory insights
- Agent registry info
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import Optional

from app.routes.middleware import get_current_user
from app.telemetry.tracer import metrics_collector, decision_logger

import structlog

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/registry")
async def list_agents(user: dict = Depends(get_current_user)):
    """List all registered agents and their capabilities."""
    from app.agents.registry import get_agent_registry
    registry = get_agent_registry()
    return {"agents": registry.list_agents()}


@router.get("/metrics")
async def get_metrics(
    days: int = Query(default=7, le=30),
    user: dict = Depends(get_current_user),
):
    """Get agent execution metrics for the last N days."""
    metrics = await metrics_collector.get_agent_metrics(days=days)
    return {"metrics": metrics, "days": days}


@router.get("/decisions")
async def get_decisions(
    email_id: Optional[str] = None,
    agent: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    user: dict = Depends(get_current_user),
):
    """Get agent decision logs for debugging."""
    user_id = user["user_id"]
    decisions = await decision_logger.get_decisions(
        user_id=user_id,
        email_id=email_id,
        agent=agent,
        limit=limit,
    )
    return {"decisions": decisions}


@router.get("/traces")
async def get_traces(
    limit: int = Query(default=20, le=100),
    user: dict = Depends(get_current_user),
):
    """Get recent execution traces."""
    from app.core.database import get_database
    db = get_database()
    user_id = user["user_id"]

    cursor = db.execution_traces.find(
        {"user_id": user_id},
        {
            "trace_id": 1, "email_id": 1, "status": 1,
            "total_duration_ms": 1, "total_tokens": 1,
            "routing_path": 1, "started_at": 1, "_id": 0,
        },
    ).sort("started_at", -1).limit(limit)

    traces = await cursor.to_list(length=limit)
    return {"traces": traces}


@router.get("/traces/{trace_id}")
async def get_trace_detail(
    trace_id: str,
    user: dict = Depends(get_current_user),
):
    """Get full detail of a specific execution trace."""
    from app.core.database import get_database
    db = get_database()
    user_id = user["user_id"]

    trace = await db.execution_traces.find_one(
        {"trace_id": trace_id, "user_id": user_id},
        {"_id": 0},
    )

    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")

    return trace


@router.get("/memory/{sender_email}")
async def get_sender_memory(
    sender_email: str,
    user: dict = Depends(get_current_user),
):
    """Get memory data about a specific sender."""
    from app.memory.store import get_memory_store
    user_id = user["user_id"]
    memory = get_memory_store()

    memories = await memory.long_term.recall_sender_memory(user_id, sender_email)
    episodes = await memory.episodic.recall_similar_episodes(user_id, sender_email=sender_email)

    return {
        "sender_email": sender_email,
        "memories": memories,
        "episodes": episodes,
    }
