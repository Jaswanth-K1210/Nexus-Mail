"""
Nexus Mail — Analytics Routes
Email analytics, trends, and insights endpoints.
"""

from fastapi import APIRouter, Depends
from app.routes.middleware import get_current_user
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])
analytics = AnalyticsService()


@router.get("/dashboard")
async def dashboard_stats(user: dict = Depends(get_current_user)):
    """Overview stats: totals, unread, pending actions, read rate."""
    return await analytics.get_dashboard_stats(user["user_id"])


@router.get("/volume")
async def daily_volume(days: int = 30, user: dict = Depends(get_current_user)):
    """Daily email volume for the past N days (chart data)."""
    return {"data": await analytics.get_daily_volume(user["user_id"], days)}


@router.get("/top-senders")
async def top_senders(limit: int = 10, user: dict = Depends(get_current_user)):
    """Top N senders by email count."""
    return {"data": await analytics.get_top_senders(user["user_id"], limit)}


@router.get("/top-domains")
async def top_domains(limit: int = 10, user: dict = Depends(get_current_user)):
    """Top N domains by email count."""
    return {"data": await analytics.get_top_domains(user["user_id"], limit)}


@router.get("/categories")
async def category_breakdown(user: dict = Depends(get_current_user)):
    """Email count per AI-assigned category (pie/bar chart)."""
    return {"data": await analytics.get_category_breakdown(user["user_id"])}


@router.get("/hourly-pattern")
async def hourly_pattern(user: dict = Depends(get_current_user)):
    """Email receive pattern by hour of day."""
    return {"data": await analytics.get_hourly_pattern(user["user_id"])}
