import asyncio
from app.core.database import connect_to_mongo, close_mongo_connection, get_database

async def run():
    await connect_to_mongo()
    db = get_database()
    
    # Prune non-essential emails from the database 
    priority_categories = ["important", "requires_response", "meeting_invitation"]
    
    result = await db.emails.delete_many({
        "category": {"$nin": priority_categories}
    })
    
    print(f"Aggressive Zero-Data Policy Applied: Successfully deleted {result.deleted_count} non-priority emails from the database.")
    
    # Strip heavy data from the remaining emails
    result2 = await db.emails.update_many(
        {"category": {"$in": priority_categories}},
        {"$unset": {"body_html": "", "body_text": ""}}
    )
    print(f"Stripped HTML/Text payload from {result2.modified_count} priority emails.")
    
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(run())
