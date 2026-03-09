import asyncio
from app.main import app
from httpx import AsyncClient, ASGITransport
from app.core.security import create_access_token
from app.core.database import connect_to_mongo, close_mongo_connection

async def test_api():
    await connect_to_mongo()
    token = create_access_token({"sub": "69ac4718fe607d80baebda41", "email": "amazinghunter1229@gmail.com"})
    headers = {"Authorization": f"Bearer {token}"}
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/gmail/emails", headers=headers)
        print("Status:", res.status_code)
        data = res.json()
        print("Keys:", data.keys())
        print("Emails count:", len(data.get("emails", [])))
        
        # Test analytics
        res2 = await ac.get("/api/analytics/categories", headers=headers)
        print("Categories:", res2.json())
        
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(test_api())
