import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
import structlog

from app.core.database import get_database
from app.services.gmail_service import GmailService
from app.ai_worker.pipeline import ProcessingPipeline

logger = structlog.get_logger(__name__)
scheduler = AsyncIOScheduler(jobstores={"default": MemoryJobStore()})


async def sync_emails_for_all_users():
    """Iterate through all users in the DB and trigger incremental sync & processing."""
    try:
        db = get_database()

        # Only sync users who have linked Google credentials
        linked_user_ids = await db.google_tokens.distinct("user_id")
        if not linked_user_ids:
            logger.info("Background sync complete", users_synced=0)
            return

        gmail_service = GmailService()
        pipeline = ProcessingPipeline()

        count = 0
        for user_id in linked_user_ids:
            try:
                # 1. Sync new emails
                await gmail_service.sync_emails(user_id)
                # 2. Process unprocessed emails
                await pipeline.process_unprocessed_emails(user_id, limit=20)
                count += 1
            except Exception as e:
                logger.error("Error in background sync for user", user_id=user_id, error=str(e))
                
        logger.info("Background sync complete", users_synced=count)
    except Exception as e:
        logger.error("Error during global background sync", error=str(e))


def setup_background_tasks():
    """Schedule the background jobs."""
    scheduler.add_job(
        sync_emails_for_all_users,
        "interval",
        minutes=15,
        id="auto_sync_emails",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Background worker started. Jobs scheduled.")


def shutdown_background_tasks():
    """Shut down the background jobs."""
    scheduler.shutdown()
    logger.info("Background worker shut down.")
