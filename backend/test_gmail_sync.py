import asyncio
from app.services.gmail_service import GmailService
from app.core.database import connect_to_mongo, close_mongo_connection
from app.core.redis_client import connect_to_redis, close_redis_connection

async def test_sync():
    await connect_to_mongo()
    await connect_to_redis()
    
    gmail_service = GmailService()
    try:
        result = await gmail_service.sync_emails('69ac4718fe607d80baebda41')
        print(f"Sync result: {result}")
    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()

    await close_redis_connection()
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(test_sync())
