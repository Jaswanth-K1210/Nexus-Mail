import asyncio
from app.core.database import connect_to_mongo, close_mongo_connection, get_database

async def run():
    await connect_to_mongo()
    db = get_database()
    
    # Drop all emails to force a fresh pull from Gmail
    await db.emails.delete_many({})
    
    # Reset user sync state
    await db.users.update_many({}, {"$unset": {"last_history_id": "", "last_sync": ""}})
    
    print("Database cleared. Next 'Force Sync' will perform a complete fresh pull from Gmail.")
    
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(run())
