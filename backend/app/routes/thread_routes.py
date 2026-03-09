"""
Nexus Mail — Thread Routes
Endpoints to retrieve full thread summaries.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from app.routes.middleware import get_current_user
from app.services.thread_service import ThreadService

router = APIRouter(prefix="/threads", tags=["Thread Summarization"])
thread_service = ThreadService()


@router.get("/{thread_id}/summary")
async def get_thread_summary(
    thread_id: str,
    force_refresh: bool = Query(False, description="Force LLM regeneration"),
    user: dict = Depends(get_current_user),
):
    """
    Get an AI-generated summary of the entire email thread.
    Includes key decisions, actionable items, and open questions.
    """
    summary = await thread_service.get_thread_summary(
        user["user_id"], thread_id, force_refresh
    )
    
    if summary and "error" in summary:
        raise HTTPException(status_code=400, detail=summary["error"])
        
    return summary
