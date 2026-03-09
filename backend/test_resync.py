import asyncio
from app.services.gmail_service import GmailService
from app.ai_worker.pipeline import ProcessingPipeline
from app.core.database import connect_to_mongo, close_mongo_connection, get_database
from app.core.redis_client import connect_to_redis, close_redis_connection

async def resync():
    await connect_to_mongo()
    await connect_to_redis()
    db = get_database()
    
    # Get user 
    user = await db.users.find_one({})
    if user:
        print("Pulling emails from Gmail...")
        service = GmailService()
        await service.sync_emails(str(user["_id"]))
        
        print("Processing new emails through AI Pipeline...")
        pipeline = ProcessingPipeline()
        await pipeline.process_unprocessed_emails(str(user["_id"]))
        
        print("Done!")
    else:
        print("No user found in DB.")
        
    await close_redis_connection()
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(resync())
