import asyncio
from app.core.database import connect_to_mongo, close_mongo_connection, get_database
from app.ai_worker.pipeline import ProcessingPipeline
from app.core.redis_client import connect_to_redis, close_redis_connection

async def run():
    await connect_to_mongo()
    await connect_to_redis()
    pipeline = ProcessingPipeline()
    db = get_database()
    
    email = await db.emails.find_one()
    if not email:
        print("No email found.")
        return
    user_id = email.get("user_id")
    
    # reset emails
    result = await db.emails.update_many(
        {},
        {"$set": {"is_processed": False}}
    )
    print(f"Reset {result.modified_count} emails for reprocessing. Using user_id {user_id}")
    
    # Process
    res = await pipeline.process_unprocessed_emails(user_id, limit=50)
    print("Reprocessed:", res)

    await close_redis_connection()
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(run())
