"""
Nexus Mail — Google OAuth & Auth Service
Handles the complete Google OAuth flow, token management, and user creation.
Per v3.1 spec: single consent screen for Gmail + Calendar scopes.
"""

from datetime import datetime, timezone
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.core.config import get_settings
from app.core.database import get_database
from app.core.security import encrypt_token, decrypt_token, create_access_token

import structlog

logger = structlog.get_logger(__name__)


class AuthService:
    """Manages Google OAuth flow, token storage, and user sessions."""

    def __init__(self):
        self.settings = get_settings()

    def get_authorization_url(self, state: str | None = None) -> str:
        """
        Generate the Google OAuth consent URL.
        Requests all scopes (Gmail + Calendar) in a single consent screen.
        """
        flow = Flow.from_client_config(
            client_config={
                "web": {
                    "client_id": self.settings.google_client_id,
                    "client_secret": self.settings.google_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.settings.google_redirect_uri],
                }
            },
            scopes=self.settings.google_oauth_scopes,
        )
        flow.redirect_uri = self.settings.google_redirect_uri

        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state=state,
        )
        return auth_url

    async def handle_callback(
        self,
        code: str,
        consent_given: bool,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        """
        Handle the Google OAuth callback. Per v3.1 spec:
        - Requires consent_given=True or returns 400
        - Exchanges code for tokens
        - Creates or updates user
        - Stores encrypted tokens
        - Returns JWT access token
        """
        if not consent_given:
            raise ValueError("Terms and conditions acceptance required")

        # Exchange authorization code for tokens
        flow = Flow.from_client_config(
            client_config={
                "web": {
                    "client_id": self.settings.google_client_id,
                    "client_secret": self.settings.google_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.settings.google_redirect_uri],
                }
            },
            scopes=self.settings.google_oauth_scopes,
        )
        flow.redirect_uri = self.settings.google_redirect_uri
        flow.fetch_token(code=code)

        credentials = flow.credentials

        # Get user info from Google
        user_info = await self._get_user_info(credentials)

        # Check which scopes were actually granted
        granted_scopes = credentials.scopes or []
        calendar_granted = (
            "https://www.googleapis.com/auth/calendar.readonly" in granted_scopes
            or "https://www.googleapis.com/auth/calendar.events" in granted_scopes
        )

        db = get_database()

        # Create or update user
        user = await self._upsert_user(
            db, user_info, consent_given, ip_address, user_agent, calendar_granted
        )

        # Store encrypted tokens
        await self._store_tokens(
            db, str(user["_id"]), credentials, granted_scopes, calendar_granted
        )

        # If calendar connected, fetch user's timezone
        if calendar_granted:
            try:
                tz = await self._get_calendar_timezone(credentials)
                await db.users.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"calendar_timezone": tz}}
                )
            except Exception as e:
                logger.warning("Could not fetch calendar timezone", error=str(e))

        # Create JWT
        access_token = create_access_token(
            data={"sub": str(user["_id"]), "email": user["email"]}
        )

        logger.info(
            "OAuth callback successful",
            user_email=user["email"],
            calendar_connected=calendar_granted,
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": str(user["_id"]),
                "email": user["email"],
                "name": user["name"],
                "profile_picture": user.get("profile_picture"),
                "calendar_connected": calendar_granted,
            },
        }

    async def demo_login(self) -> dict:
        """Create a mock user and return a valid JWT for testing the UI without Google credentials."""
        db = get_database()
        user_info = {
            "email": "demo@nexusmail.app",
            "name": "Nexus Demo User",
            "id": "demo-google-id-12345",
            "picture": "https://ui-avatars.com/api/?name=Nexus&background=B19EEF&color=fff"
        }
        user = await self._upsert_user(
            db, user_info, True, "127.0.0.1", "demo-agent", False
        )
        access_token = create_access_token(
            data={"sub": str(user["_id"]), "email": user["email"]}
        )
        
        logger.info("Demo login successful", user_email=user["email"])
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": str(user["_id"]),
                "email": user["email"],
                "name": user["name"],
                "profile_picture": user.get("profile_picture"),
                "calendar_connected": False,
            },
        }

    async def _get_user_info(self, credentials: Credentials) -> dict:
        """Fetch user profile from Google People API."""
        service = build("oauth2", "v2", credentials=credentials)
        user_info = service.userinfo().get().execute()
        return user_info

    async def _upsert_user(
        self,
        db,
        user_info: dict,
        consent_given: bool,
        ip_address: str | None,
        user_agent: str | None,
        calendar_granted: bool,
    ) -> dict:
        """Create a new user or update existing one."""
        now = datetime.now(timezone.utc)

        user_doc = {
            "email": user_info["email"],
            "name": user_info.get("name", ""),
            "google_id": user_info["id"],
            "profile_picture": user_info.get("picture"),
            "calendar_connected": calendar_granted,
            "updated_at": now,
        }

        # Set consent on first signup
        consent_update = {
            "consent.given": consent_given,
            "consent.timestamp": now,
            "consent.version": "v1.0",
            "consent.ip_address": ip_address,
            "consent.user_agent": user_agent,
        }

        result = await db.users.find_one_and_update(
            {"google_id": user_info["id"]},
            {
                "$set": {**user_doc, **consent_update},
                "$setOnInsert": {"created_at": now, "tone_profile": None},
            },
            upsert=True,
            return_document=True,
        )
        return result

    async def _store_tokens(
        self,
        db,
        user_id: str,
        credentials: Credentials,
        granted_scopes: list,
        calendar_granted: bool,
    ) -> None:
        """Store encrypted Google OAuth tokens in google_tokens collection."""
        now = datetime.now(timezone.utc)

        token_doc = {
            "user_id": user_id,
            "access_token": encrypt_token(credentials.token),
            "refresh_token": encrypt_token(credentials.refresh_token or ""),
            "token_expiry": credentials.expiry,
            "token_scopes": list(granted_scopes),
            "calendar_scope_granted": calendar_granted,
            "updated_at": now,
        }

        await db.google_tokens.update_one(
            {"user_id": user_id},
            {"$set": token_doc, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )

    async def _get_calendar_timezone(self, credentials: Credentials) -> str:
        """Fetch the user's primary calendar timezone."""
        service = build("calendar", "v3", credentials=credentials)
        calendar = service.calendarList().get(calendarId="primary").execute()
        return calendar.get("timeZone", "UTC")

    async def get_user_credentials(self, user_id: str) -> Credentials | None:
        """
        Retrieve and decrypt user's Google credentials.
        Handles token refresh if expired.
        """
        db = get_database()
        token_doc = await db.google_tokens.find_one({"user_id": user_id})

        if not token_doc:
            return None

        access_token = decrypt_token(token_doc["access_token"])
        refresh_token = decrypt_token(token_doc["refresh_token"])

        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.settings.google_client_id,
            client_secret=self.settings.google_client_secret,
            scopes=token_doc.get("token_scopes", []),
        )

        # Refresh if expired
        if credentials.expired and credentials.refresh_token:
            from google.auth.transport.requests import Request
            credentials.refresh(Request())

            # Store refreshed tokens
            await db.google_tokens.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "access_token": encrypt_token(credentials.token),
                        "token_expiry": credentials.expiry,
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )
            logger.info("Refreshed Google tokens", user_id=user_id)

        return credentials

    async def get_consent_status(self, user_id: str) -> dict:
        """Check if user has valid consent record."""
        db = get_database()
        user = await db.users.find_one(
            {"_id": user_id},
            {"consent": 1, "calendar_connected": 1}
        )
        if not user:
            return {"consent_given": False, "calendar_connected": False}

        consent = user.get("consent", {})
        return {
            "consent_given": consent.get("given", False),
            "consent_version": consent.get("version"),
            "calendar_connected": user.get("calendar_connected", False),
        }
