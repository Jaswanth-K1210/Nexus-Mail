"""
Nexus Mail — FastAPI Application Entry Point
v3.1: Gmail + Calendar + Meeting Intelligence + Desktop Notifications
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import connect_to_mongo, close_mongo_connection
from app.core.redis_client import connect_to_redis, close_redis_connection
from app.core.rate_limit import limiter
from app.worker import setup_background_tasks, shutdown_background_tasks

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.routes.auth_routes import router as auth_router
from app.routes.gmail_routes import router as gmail_router
from app.routes.meeting_routes import router as meeting_router
from app.routes.analytics_routes import router as analytics_router
from app.routes.unsubscribe_routes import router as unsubscribe_router
from app.routes.reply_tracker_routes import router as reply_tracker_router
from app.routes.cold_email_routes import router as cold_email_router
from app.routes.sse_routes import router as sse_router
from app.routes.tone_routes import router as tone_router
from app.routes.draft_routes import router as draft_router
from app.routes.rules_routes import router as rules_router
from app.routes.thread_routes import router as thread_router
from app.routes.sender_routes import router as sender_router
from app.routes.webhook_routes import router as webhook_router
from app.routes.assistant_routes import router as assistant_router

import structlog

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    # Startup
    logger.info("Starting Nexus Mail backend v3.1")
    await connect_to_mongo()
    await connect_to_redis()
    setup_background_tasks()
    logger.info("All connections established")
    yield
    # Shutdown
    logger.info("Shutting down Nexus Mail backend")
    shutdown_background_tasks()
    await close_redis_connection()
    await close_mongo_connection()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Nexus Mail API",
        description="AI-powered email assistant with Meeting Intelligence",
        version="3.1.0",
        lifespan=lifespan,
    )

    # ─── CORS ───
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )

    # ─── Rate Limiting ───
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ─── Routes ───
    app.include_router(auth_router, prefix="/api")
    app.include_router(gmail_router, prefix="/api")
    app.include_router(meeting_router, prefix="/api")
    app.include_router(analytics_router, prefix="/api")
    app.include_router(unsubscribe_router, prefix="/api")
    app.include_router(reply_tracker_router, prefix="/api")
    app.include_router(cold_email_router, prefix="/api")
    app.include_router(sse_router, prefix="/api")
    app.include_router(tone_router, prefix="/api")
    app.include_router(draft_router, prefix="/api")
    app.include_router(rules_router, prefix="/api")
    app.include_router(thread_router, prefix="/api")
    app.include_router(sender_router, prefix="/api")
    app.include_router(webhook_router, prefix="/api")
    app.include_router(assistant_router, prefix="/api")

    # ─── Health Check ───
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "version": "3.1.0",
            "app": settings.app_name,
        }

    @app.get("/")
    async def root():
        return {
            "app": "Nexus Mail",
            "version": "3.1.0",
            "docs": "/docs",
            "description": "AI-powered email assistant with Meeting Intelligence",
        }

    return app


# Create the app instance
app = create_app()
