"""
Nexus Mail — Pydantic Schemas
Request/response models for API endpoints and internal data structures.
Follows the v3.1 backend spec MongoDB schema exactly.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────

class AIProvider(str, Enum):
    GROQ = "groq"
    OPENAI = "openai"


class EmailCategory(str, Enum):
    IMPORTANT = "important"
    REQUIRES_RESPONSE = "requires_response"
    MEETING_INVITATION = "meeting_invitation"
    NEWSLETTER = "newsletter"
    PROMOTIONAL = "promotional"
    SOCIAL = "social"
    TRANSACTIONAL = "transactional"
    SPAM = "spam"


class AvailabilityStatus(str, Enum):
    FREE = "free"
    PARTIAL = "partial"
    BUSY = "busy"


class MeetingAlertStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    SUGGESTED = "suggested"
    DISMISSED = "dismissed"


class MeetingPlatform(str, Enum):
    GOOGLE_MEET = "google_meet"
    ZOOM = "zoom"
    TEAMS = "teams"
    CALENDLY = "calendly"
    OTHER = "other"


class UserResponse(str, Enum):
    YES = "yes"
    NO = "no"
    SUGGEST = "suggest"


# ──────────────────────────────────────────────
# User Models
# ──────────────────────────────────────────────

class ConsentRecord(BaseModel):
    given: bool = False
    timestamp: Optional[datetime] = None
    version: str = "v1.0"
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class UserInDB(BaseModel):
    """User document as stored in MongoDB users collection."""
    email: EmailStr
    name: str
    google_id: str
    profile_picture: Optional[str] = None
    consent: ConsentRecord = ConsentRecord()
    calendar_connected: bool = False
    calendar_timezone: Optional[str] = None
    tone_profile: Optional[dict] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())


class UserResponse(BaseModel):
    """User data returned to frontend."""
    id: str
    email: str
    name: str
    profile_picture: Optional[str] = None
    calendar_connected: bool = False
    consent_given: bool = False


# ──────────────────────────────────────────────
# Google Tokens (renamed from gmail_tokens per v3.1 spec)
# ──────────────────────────────────────────────

class GoogleTokensInDB(BaseModel):
    """Google OAuth tokens stored encrypted in google_tokens collection."""
    user_id: str
    access_token: str  # AES-256-GCM encrypted
    refresh_token: str  # AES-256-GCM encrypted
    token_expiry: datetime
    token_scopes: List[str] = []
    calendar_scope_granted: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())


# ──────────────────────────────────────────────
# Email Models
# ──────────────────────────────────────────────

class EmailInDB(BaseModel):
    """Email document as stored in MongoDB emails collection."""
    user_id: str
    gmail_id: str
    thread_id: str
    subject: str = ""
    sender_name: str = ""
    sender_email: str = ""
    snippet: str = ""
    body_text: str = ""
    body_html: str = ""
    received_at: Optional[datetime] = None
    labels: List[str] = []
    is_read: bool = False
    is_processed: bool = False
    # AI-generated fields
    category: Optional[str] = None
    severity: Optional[int] = None  # 1-5
    summary: Optional[str] = None
    action_items: List[str] = []
    risk_flags: List[str] = []
    reply_draft: Optional[str] = None
    # Meeting-specific fields (v3.1)
    is_meeting_invitation: bool = False
    has_meeting_alert: bool = False
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    processed_at: Optional[datetime] = None


# ──────────────────────────────────────────────
# Meeting Alert Models (v3.1)
# ──────────────────────────────────────────────

class ConflictEvent(BaseModel):
    """A conflicting Google Calendar event."""
    title: str
    start: datetime
    end: datetime


class MeetingAlertInDB(BaseModel):
    """Meeting alert document as stored in MongoDB meeting_alerts collection."""
    user_id: str
    email_id: str
    sender_name: str
    sender_email: str
    proposed_datetime: datetime  # UTC
    proposed_timezone: str
    duration_minutes: int = 60
    meeting_link: Optional[str] = None
    meeting_platform: str = "other"
    availability: str = "free"  # free | partial | busy
    conflict_events: List[ConflictEvent] = []
    status: str = "pending"  # pending | accepted | declined | suggested | dismissed
    user_response: Optional[str] = None  # yes | no | suggest
    suggested_time: Optional[datetime] = None
    reply_sent: bool = False
    calendar_event_id: Optional[str] = None
    notification_sent: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    resolved_at: Optional[datetime] = None


# ──────────────────────────────────────────────
# API Request/Response Models
# ──────────────────────────────────────────────

class AuthCallbackRequest(BaseModel):
    code: str
    state: Optional[str] = None
    consent_given: bool = False
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class MeetingAcceptResponse(BaseModel):
    calendar_event_id: str
    reply_preview: str
    event_title: str
    event_time: str


class MeetingDeclineRequest(BaseModel):
    reason: Optional[str] = None


class MeetingDeclineResponse(BaseModel):
    reply_preview: str


class MeetingSuggestRequest(BaseModel):
    suggested_datetime: str  # ISO 8601


class MeetingSuggestResponse(BaseModel):
    reply_preview: str


class AvailableSlot(BaseModel):
    start: datetime
    end: datetime
    label: str  # e.g. "Friday Mar 8 · 10:00 AM"


class AvailabilityResponse(BaseModel):
    available_slots: List[AvailableSlot]


class GmailStatusResponse(BaseModel):
    connected: bool
    last_sync: Optional[str] = None
    emails_synced: int = 0
    processed_today: int = 0
    ai_provider: str = "groq"
    pending_alerts: List[dict] = []


class MeetingAlertResponse(BaseModel):
    id: str
    type: str = "meeting_invitation"
    sender_name: str
    sender_email: str
    proposed_time: str
    duration_min: int
    availability: str
    meeting_link: Optional[str] = None
    status: str = "pending"
