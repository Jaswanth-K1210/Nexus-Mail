import asyncio
from app.services.auth_service import AuthService
from app.core.database import connect_to_mongo, close_mongo_connection
from googleapiclient.discovery import build

async def test_get_one():
    await connect_to_mongo()
    auth = AuthService()
    user_id = '69ac4718fe607d80baebda41'
    credentials = await auth.get_user_credentials(user_id)
    if not credentials:
        print("No creds found")
        return
    
    try:
        service = build("gmail", "v1", credentials=credentials)
        print("Got Gmail service")
        # Try getting messages
        messages_result = service.users().messages().list(
            userId="me", q="in:inbox", maxResults=5
        ).execute()
        
        print("MESSAGES:")
        for msg in messages_result.get("messages", []):
            try:
                full_msg = service.users().messages().get(
                    userId="me", id=msg["id"], format="full"
                ).execute()
                headers = {h["name"]: h["value"] for h in full_msg["payload"]["headers"]}
                print(f"- {headers.get('Subject')} (From: {headers.get('From')})")
            except Exception as e:
                print(f"Error fetching message {msg['id']}: {e}")

    except Exception as e:
        print(f"Failed: {e}")

    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(test_get_one())
