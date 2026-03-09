import asyncio
from app.core.database import connect_to_mongo, close_mongo_connection, get_database

async def count_docs():
    await connect_to_mongo()
    db = get_database()
    count = await db.emails.count_documents({})
    all_emails = await db.emails.find({}).to_list(None)
    print(f"Total emails in DB: {count}")
    for e in all_emails:
        print(e.get('subject'), e.get('is_processed'))
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(count_docs())
