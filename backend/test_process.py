import asyncio
from app.ai_worker.pipeline import ProcessingPipeline
from app.core.database import connect_to_mongo, close_mongo_connection
from app.core.redis_client import connect_to_redis, close_redis_connection

async def test_process():
    await connect_to_mongo()
    await connect_to_redis()
    
    pipeline = ProcessingPipeline()
    try:
        result = await pipeline.process_unprocessed_emails('69ac4718fe607d80baebda41', limit=5)
        print(f"Process result: {result}")
    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()

    await close_redis_connection()
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(test_process())
