import asyncio
from app.core.database import connect_to_mongo, close_mongo_connection

async def run():
    await connect_to_mongo()
    await close_mongo_connection()
    print("Indexes applied successfully")

if __name__ == "__main__":
    asyncio.run(run())
