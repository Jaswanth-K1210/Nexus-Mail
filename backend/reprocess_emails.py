import asyncio
from app.core.database import connect_to_mongo, close_mongo_connection, get_database
from app.ai_worker.pipeline import ProcessingPipeline
from app.core.redis_client import connect_to_redis, close_redis_connection

async def run():
    await connect_to_mongo()
    await connect_to_redis()
    pipeline = ProcessingPipeline()
    db = get_database()
    
    # reset emails
    result = await db.emails.update_many(
        {"$or": [
            {"sender_name": {"$regex": "umesh|hunter|amazinghunter", "$options": "i"}},
            {"sender_email": {"$regex": "umesh|hunter|amazinghunter", "$options": "i"}},
            {"subject": {"$regex": "emergency|catch up", "$options": "i"}}
        ]},
        {"$set": {"is_processed": False}}
    )
    print(f"Reset {result.modified_count} emails for reprocessing.")
    
    # Process
    res = await pipeline.process_unprocessed_emails("69ac4718fe607d80baebda41", limit=10)
    print("Reprocessed:", res)

    await close_redis_connection()
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(run())
