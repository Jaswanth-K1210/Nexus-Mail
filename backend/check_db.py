import asyncio
from app.core.database import get_database

async def main():
    db = get_database()
    emails = await db.emails.find().to_list(10)
    for e in emails:
        print(f"Subject: {e.get('subject')}")
        print(f"Summary: {e.get('summary')}")
        print("-" * 40)
        
    drafts = await db.email_drafts.find().to_list(10)
    for d in drafts:
        print(f"Draft for {d.get('subject')}: {d.get('draft_body')[:50]}... Conf: {d.get('ai_confidence')}")

if __name__ == "__main__":
    asyncio.run(main())
