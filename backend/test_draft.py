import asyncio
from app.ai_worker.tasks.reply_draft import generate_reply_draft

async def main():
    res = await generate_reply_draft(
        subject="Test",
        body="Hello",
        sender="test@test.com",
        sender_name="Test"
    )
    print("Response:", res)

if __name__ == "__main__":
    asyncio.run(main())
