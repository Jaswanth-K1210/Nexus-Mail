import asyncio
from app.services.auth_service import AuthService
from app.core.database import connect_to_mongo, close_mongo_connection
from googleapiclient.discovery import build
import email.mime.text
import base64

async def send_test_emails():
    # Setup test scenarios
    tests = [
        {
            "to": "amazinghunter1229@gmail.com",
            "subject": "Quick Catch Up - Marketing Strategy alignment",
            "body": "Hey Jaswanth,\n\nI was hoping we could jump on a quick call tomorrow at 10 AM PST to discuss the marketing strategy for the upcoming Q3 launch. Let me know if that works or if we should suggest another time.\n\nBest,\nSarah"
        },
        {
            "to": "amazinghunter1229@gmail.com",
            "subject": "Action Required: Complete Security Training by Friday",
            "body": "Hello,\n\nPlease complete your mandatory 2026 security awareness training by this Friday at 5:00 PM EST. This is required for all engineering personnel.\n\nAccess the portal here: https://security.nexus-internal.app\n\nThanks,\nCompliance Team"
        },
        {
            "to": "amazinghunter1229@gmail.com",
            "subject": "Your Next Stripe Invoice is available",
            "body": "Your upcoming invoice for the period of Feb 1 - Mar 1 is now generated. The amount of $49.00 will be charged to the card on file ending in 4242 in 3 days. You can view the full details of this transaction on your billing dashboard."
        }
    ]

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
        
        for idx, t in enumerate(tests):
            message = email.mime.text.MIMEText(t["body"])
            message["to"] = t["to"]
            message["subject"] = t["subject"]
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            
            result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
            print(f"Sent email {idx+1}: {t['subject']}")
            
    except Exception as e:
        print(f"Failed: {e}")

    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(send_test_emails())
