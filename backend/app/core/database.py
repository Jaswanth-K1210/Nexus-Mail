"""
Nexus Mail — MongoDB Connection Manager
Uses Motor (async MongoDB driver) for non-blocking database operations.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import get_settings
import structlog

logger = structlog.get_logger(__name__)

# Module-level client and db references
_client: AsyncIOMotorClient | None = None
_database: AsyncIOMotorDatabase | None = None


async def connect_to_mongo() -> None:
    """Initialize MongoDB connection and create indexes."""
    global _client, _database
    settings = get_settings()

    logger.info("Connecting to MongoDB", uri=settings.mongodb_uri[:30] + "...")
    _client = AsyncIOMotorClient(settings.mongodb_uri)
    _database = _client[settings.mongodb_database]

    # Verify connection
    await _client.admin.command("ping")
    logger.info("MongoDB connected", database=settings.mongodb_database)

    # Create indexes as specified in v3.1 spec
    await _create_indexes()


async def _create_indexes() -> None:
    """Create MongoDB indexes for performance."""
    db = get_database()

    # users collection
    await db.users.create_index("email", unique=True)
    await db.users.create_index("google_id", unique=True)

    # emails collection
    await db.emails.create_index([("user_id", 1), ("gmail_id", 1)], unique=True)
    await db.emails.create_index([("user_id", 1), ("is_processed", 1)])
    await db.emails.create_index([("user_id", 1), ("category", 1), ("received_at", -1)])
    await db.emails.create_index([("user_id", 1), ("is_meeting_invitation", 1)])
    
    # Zero-Data SaaS Retention Protocol: Purge emails after configured days.
    # Set email_retention_days=0 to disable auto-deletion.
    settings = get_settings()
    if settings.email_retention_days > 0:
        await db.emails.create_index("received_at", expireAfterSeconds=settings.email_retention_days * 24 * 60 * 60)

    # google_tokens collection (renamed from gmail_tokens per v3.1 spec)
    await db.google_tokens.create_index("user_id", unique=True)

    # meeting_alerts collection
    await db.meeting_alerts.create_index(
        [("user_id", 1), ("status", 1), ("created_at", -1)]
    )

    # email_threads collection
    await db.email_threads.create_index([("user_id", 1), ("thread_id", 1)], unique=True)

    # unsubscribe_preferences collection (Bulk Unsubscriber)
    await db.unsubscribe_preferences.create_index(
        [("user_id", 1), ("sender_email", 1)], unique=True
    )

    # cold_email_settings collection (Cold Email Blocker)
    await db.cold_email_settings.create_index("user_id", unique=True)

    # sender_whitelist collection (Cold Email Blocker)
    await db.sender_whitelist.create_index(
        [("user_id", 1), ("sender_email", 1)], unique=True
    )

    # email_drafts collection (Draft-First Mode)
    await db.email_drafts.create_index([("user_id", 1), ("status", 1)])
    await db.email_drafts.create_index([("user_id", 1), ("created_at", -1)])

    # user_rules collection (Natural Language Rules)
    await db.user_rules.create_index([("user_id", 1), ("is_active", 1)])

    # sender_profiles collection (Sender Intelligence)
    await db.sender_profiles.create_index(
        [("user_id", 1), ("sender_email", 1)], unique=True
    )

    logger.info("MongoDB indexes created")


async def close_mongo_connection() -> None:
    """Close MongoDB connection."""
    global _client, _database
    if _client:
        _client.close()
        _client = None
        _database = None
        logger.info("MongoDB connection closed")


def get_database() -> AsyncIOMotorDatabase:
    """Get the database instance. Must call connect_to_mongo() first."""
    if _database is None:
        raise RuntimeError("Database not initialized. Call connect_to_mongo() first.")
    return _database
