# Nexus Mail — Complete Feature Map
### AI-Powered Email Assistant with Meeting Intelligence
**Version:** 3.1 · **Last Updated:** March 6, 2026

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Phase 2 — React)                   │
│         Apple-style Glassmorphism Design · Dark Mode             │
│   Dashboard · Email List · Meeting Cards · Analytics Charts     │
├─────────────────────────────────────────────────────────────────┤
│                          REST API                               │
│                    FastAPI (Python 3.11+)                        │
├───────────┬───────────┬───────────┬───────────┬─────────────────┤
│   Auth    │   Gmail   │ Meetings  │ Analytics │  Inbox Zero     │
│  Service  │  Service  │  Service  │  Service  │   Features      │
├───────────┴───────────┴───────────┴───────────┴─────────────────┤
│                    AI Processing Pipeline                       │
│              Groq (primary) / OpenAI (fallback)                 │
│     6 Sequential Tasks per Email · Meeting Intelligence         │
├─────────────────────────────────────────────────────────────────┤
│  MongoDB (async via Motor)  │  Google APIs (Gmail + Calendar)   │
└─────────────────────────────────────────────────────────────────┘
```

---

## FEATURE 1 — Google OAuth + Single Consent Screen

| Detail        | Value |
|---------------|-------|
| **Status**    | ✅ BUILT |
| **File**      | `services/auth_service.py` |
| **Route**     | `POST /api/auth/google/callback` |

**What it does:**
- User clicks "Sign in with Google" → redirected to Google OAuth
- Single consent screen requests ALL permissions upfront (Gmail + Calendar)
- No second popup later for calendar — it's all done in one shot

**How we do it:**
- Request 7 scopes in one `google_auth_oauthlib` flow:
  - `openid`, `userinfo.email`, `userinfo.profile`
  - `gmail.readonly`, `gmail.send`
  - `calendar.readonly`, `calendar.events`
- On callback: exchange code → get tokens → encrypt with AES-256-GCM → store in MongoDB
- Record T&C consent (timestamp, IP, user agent) for legal compliance
- Return a JWT access token for all future API calls

**API Endpoints:**
- `GET  /api/auth/google/url` — Get the consent URL
- `POST /api/auth/google/callback` — Handle callback, return JWT
- `GET  /api/auth/consent-status` — Check consent status

---

## FEATURE 2 — Gmail Email Sync

| Detail        | Value |
|---------------|-------|
| **Status**    | ✅ BUILT |
| **File**      | `services/gmail_service.py` |
| **Route**     | `POST /api/gmail/sync` |

**What it does:**
- Pulls emails from Gmail API and stores them in MongoDB
- Parses headers, extracts text/HTML bodies (handles nested multipart)
- Base64 URL-safe decoding for Gmail's content format
- Tracks sync state — only fetches new emails each time

**How we do it:**
- `gmail.users().messages().list()` → get message IDs
- Skip already-synced emails (check `gmail_id` in DB)
- For each new email: `messages().get(format="full")` → parse headers, extract body
- Store with fields: `user_id`, `gmail_id`, `thread_id`, `subject`, `sender_name`, `sender_email`, `snippet`, `body_text`, `body_html`, `received_at`, `labels`, `is_read`

**API Endpoints:**
- `POST /api/gmail/sync` — Trigger email sync
- `GET  /api/gmail/status` — Sync stats + pending meeting alerts
- `GET  /api/gmail/emails` — List emails (with category filter)
- `GET  /api/gmail/emails/{id}` — Single email detail

---

## FEATURE 3 — 6-Task AI Processing Pipeline

| Detail        | Value |
|---------------|-------|
| **Status**    | ✅ BUILT |
| **File**      | `ai_worker/pipeline.py` |
| **Route**     | `POST /api/gmail/process` |

**What it does:**
Every email flows through 6 AI tasks in sequence. The pipeline is the brain of Nexus Mail.

**How we do it:**
Each task calls Groq API (or OpenAI fallback) with a specialized prompt. The pipeline orchestrator runs tasks 1→6 sequentially, passing results between tasks.

### Task 1: Email Classification (`tasks/classify.py`)
- Classifies into **8 categories**: important, requires_response, meeting_invitation, newsletter, promotional, social, transactional, spam
- Assigns **severity** (1-5)
- Detects meeting invitations using **multi-signal approach**:
  - Subject keywords: "meeting", "schedule", "calendar invite"
  - Body patterns: date/time mentions, availability questions
  - Meeting links: Zoom, Google Meet, Teams URLs
  - .ics attachment presence

### Task 2: Meeting Intelligence (`tasks/meeting_intelligence.py`) — CONDITIONAL
- **Only runs if Task 1 detected a meeting invitation**
- 5-stage process:
  1. AI extracts meeting datetime, timezone, duration, link, platform
  2. Parses datetime to UTC using `python-dateutil`
  3. Queries Google Calendar API with ±15 minute buffers
  4. Determines availability: **FREE** / **PARTIAL** (adjacent) / **BUSY** (conflict)
  5. Creates a `meeting_alerts` document in MongoDB

### Task 3: Email Summarization (`tasks/summarise.py`)
- Generates a concise 2-3 sentence summary
- **Meeting emails** get a specialized prompt focusing on:
  - Who is the sender and their context?
  - What is the meeting purpose?
  - When and where?

### Task 4: Action Item Extraction (`tasks/extract_actions.py`)
- Extracts specific actionable items with:
  - Priority (high/medium/low)
  - Deadline detection
  - Action type
- **Meeting emails**: Primary action is always Accept/Decline

### Task 5: Risk & Phishing Detection (`tasks/risk_detect.py`)
- Analyzes for security risks:
  - Sender credibility check
  - Urgency manipulation tactics
  - Suspicious link detection
  - Attachment risk assessment
- **Meeting emails**: Extra validation of video conferencing URLs (is this really a Zoom link?)

### Task 6: Reply Draft Generation (`tasks/reply_draft.py`)
- Generates reply using the user's **learned tone profile**
- **Regular emails**: Pre-computed during pipeline for instant display
- **Meeting emails**: Drafts generated **on-demand** when user clicks Accept/Decline
  - *Architecture fix from Superhuman analysis: eliminates wasted LLM inference on dismissed meetings*

---

## FEATURE 4 — Meeting Intelligence Engine

| Detail        | Value |
|---------------|-------|
| **Status**    | ✅ BUILT |
| **Files**     | `services/meeting_service.py` + `tasks/meeting_intelligence.py` |
| **Routes**    | `POST /api/meetings/{id}/accept` etc. |

**What it does:**
Automatically detects meeting invitations, checks your calendar, shows conflicts, and lets you respond with one click. Like having a personal secretary.

**How we do it:**

### Detection (Pipeline Task 2):
1. AI extracts: datetime, timezone, duration, meeting link, platform
2. Converts to UTC → queries Google Calendar `events.list()`
3. Checks ±15 min buffer zone → FREE / PARTIAL / BUSY
4. Creates `meeting_alerts` document with all details

### User Response — 3 Flows:

**Accept Flow (10 steps):**
1. Verify alert is pending
2. Fetch user's tone profile
3. AI generates acceptance reply **on-demand** (not pre-computed)
4. Send reply via Gmail API
5. Create Google Calendar event (with 15min + 60min reminders)
6. Update alert status → "accepted"

**Decline Flow:**
1. AI generates polite decline **on-demand** (with optional reason)
2. Send via Gmail → update status → "declined"

**Suggest Another Time:**
1. Query calendar for next N available 1-hour slots (business hours, skip weekends)
2. User picks a slot
3. AI generates counter-proposal reply
4. Send via Gmail → move email to "awaiting_reply" category

**API Endpoints:**
- `GET  /api/meetings/pending` — All pending alerts
- `POST /api/meetings/{id}/accept` — Accept + create calendar event
- `POST /api/meetings/{id}/decline` — Decline with optional reason
- `POST /api/meetings/{id}/suggest` — Suggest alternative time
- `GET  /api/meetings/{id}/availability` — Check available slots
- `POST /api/meetings/{id}/dismiss` — Dismiss alert

---

## FEATURE 5 — Bulk Unsubscriber *(Inspired by Inbox Zero)*

| Detail        | Value |
|---------------|-------|
| **Status**    | ✅ BUILT |
| **File**      | `services/unsubscribe_service.py` |
| **Routes**    | `/api/unsubscribe/*` |

**What it does:**
Scans your inbox for newsletters and promotional emails you never read. Shows them in a list sorted by frequency, and lets you clean up in bulk.

**How we do it:**
- **MongoDB aggregation pipeline** groups emails by sender where `category` is "newsletter" or "promotional"
- Calculates per-sender stats: total count, read count, **read percentage**, last received
- Read percentage is the key metric — if you read 5% of someone's emails, you probably don't need them

**User Actions:**
- **Unsubscribe**: Attempts to use `List-Unsubscribe` email header (automated) → falls back to Gmail filter
- **Auto-Archive**: All future emails from this sender get auto-archived silently → skip inbox
- **Auto-Archive + Label**: Same but applies a custom Gmail label for later reference
- **Keep**: Hides sender from the unsubscribe list (they stay in your inbox)

**Pipeline Integration:**
- During email processing, `apply_auto_archive_rules()` is called FIRST
- If sender matches an auto-archive rule → skip ALL 6 AI tasks (saves Groq API credits)

**API Endpoints:**
- `GET  /api/unsubscribe/senders` — List with stats (sortable by count, read rate, recency)
- `POST /api/unsubscribe/unsubscribe` — One-click unsubscribe
- `POST /api/unsubscribe/auto-archive` — Set auto-archive (optional label)
- `POST /api/unsubscribe/keep` — Hide sender from list

---

## FEATURE 6 — Cold Email Blocker *(Inspired by Inbox Zero)*

| Detail        | Value |
|---------------|-------|
| **Status**    | ✅ BUILT |
| **File**      | `services/cold_email_service.py` |
| **Routes**    | `/api/cold-emails/*` |

**What it does:**
Uses AI to detect unsolicited outreach emails (sales pitches, recruiter spam, partnership requests) and automatically blocks them before they clutter your inbox.

**How we do it:**
- **First-contact check**: Queries MongoDB to see if this sender has EVER emailed you before
- **Sender whitelist**: Checks user's whitelist before running AI detection
- **AI classification**: Sends email to Groq with a specialized cold email detection prompt that looks for:
  - "I found you on LinkedIn" introductions
  - Sales pitch language ("We help companies like yours...")
  - Generic template personalization
  - Unsolicited demo/call booking links
  - Unknown recruiter outreach
- Returns `is_cold_email`, `confidence` (0-1), `cold_email_type` (sales/recruitment/partnership/spam)

**3 Modes:**
1. **List Only**: Just flags them — you see them in a separate view
2. **Auto Label**: Flags + applies a "Cold Email" label in Gmail
3. **Auto Archive + Label**: Flags + labels + archives (never hits inbox)

**Pipeline Integration:**
- Runs in the pipeline BEFORE the 6 AI tasks
- If mode is "auto_archive_label" and confidence ≥ 0.7 → skip pipeline entirely

**API Endpoints:**
- `GET  /api/cold-emails/settings` — Current blocker settings
- `PUT  /api/cold-emails/settings` — Update mode, enable/disable
- `GET  /api/cold-emails/list` — View detected cold emails
- `POST /api/cold-emails/whitelist` — Whitelist a sender

---

## FEATURE 7 — Reply Zero Tracker *(Inspired by Inbox Zero)*

| Detail        | Value |
|---------------|-------|
| **Status**    | ✅ BUILT |
| **File**      | `services/reply_tracker_service.py` |
| **Routes**    | `/api/replies/*` |

**What it does:**
Tracks two lists to ensure no email falls through the cracks:
- **"To Reply"**: Emails you need to respond to but haven't yet
- **"Awaiting Reply"**: Emails where you replied, but they haven't responded back

**How we do it:**

**To Reply List:**
- Queries emails with `category` = "requires_response" or "important"
- Where `replied` ≠ true and `reply_dismissed` ≠ true
- Calculates age → marks as **overdue** if > 48 hours without reply
- Shows AI-generated reply draft for quick send

**Awaiting Reply List:**
- Queries emails with `category` = "awaiting_reply"
- Where `response_received` ≠ true
- Marks as **overdue** if waiting > 3 days

**AI Nudge (One-Click Follow-Up):**
- When you've been waiting too long for a reply:
  - Click "Nudge" button
  - AI generates a polite 2-sentence follow-up using your tone profile
  - Preview it → send directly

**API Endpoints:**
- `GET  /api/replies/stats` — Counts for both lists + overdue counts
- `GET  /api/replies/needs-reply` — To Reply list (filterable by age)
- `GET  /api/replies/awaiting` — Awaiting Reply list
- `POST /api/replies/nudge/{id}` — AI generates follow-up nudge
- `POST /api/replies/mark-replied` — Mark as replied
- `POST /api/replies/mark-done` — Remove from all tracking

---

## FEATURE 8 — Email Analytics Dashboard *(Inspired by Inbox Zero)*

| Detail        | Value |
|---------------|-------|
| **Status**    | ✅ BUILT |
| **File**      | `services/analytics_service.py` |
| **Routes**    | `/api/analytics/*` |

**What it does:**
Gives you a complete picture of your email habits through charts and statistics.

**How we do it:**
All powered by **MongoDB aggregation pipelines** — no separate analytics DB needed.

**Dashboard Stats (Card View):**
- Total emails, today's count, this week's count
- Unread count, processed count
- Pending meetings, needs-response count
- Overall read rate percentage

**Charts & Visualizations:**
- **Daily Volume**: Received vs read count per day (line chart, configurable 7-90 days)
- **Top Senders**: Who emails you most — name, count, unread count (bar chart)
- **Top Domains**: Which organizations email you most (treemap)
- **Category Breakdown**: Pie chart of AI-categorized emails (e.g., 35% newsletters, 25% important, 15% meetings...)
- **Hourly Pattern**: Heatmap of when you receive emails by hour (0-23)

**API Endpoints:**
- `GET /api/analytics/dashboard` — Overview stat cards
- `GET /api/analytics/volume?days=30` — Daily volume chart data
- `GET /api/analytics/top-senders?limit=10` — Top senders
- `GET /api/analytics/top-domains?limit=10` — Top domains
- `GET /api/analytics/categories` — Category distribution
- `GET /api/analytics/hourly-pattern` — Hourly receive pattern

---

## FEATURE 9 — Security Layer

| Detail        | Value |
|---------------|-------|
| **Status**    | ✅ BUILT |
| **File**      | `core/security.py` + `routes/middleware.py` |

**What it does:**
Multi-layer security protecting user data and API access.

**How we do it:**
- **AES-256-GCM Encryption**: All Google tokens encrypted at rest (96-bit nonce prepended to ciphertext, base64 encoded)
- **JWT Authentication**: Bearer tokens with configurable expiry, used for all protected endpoints
- **CORS Middleware**: Configurable allowed origins
- **T&C Consent Recording**: Timestamp, IP, user agent stored for legal compliance

---

## FEATURE 10 — Real-Time SSE Notifications *(Superhuman Architecture Fix)*

| Detail        | Value |
|---------------|-------|
| **Status**    | ✅ BUILT |
| **File**      | `services/sse_service.py` |
| **Routes**    | `/api/events/*` |

**What it does:**
Replaces the 60-second polling mechanism with Server-Sent Events for instant push notifications.

**Why (from Superhuman analysis):**
> "100K users = 100K requests/minute solely for status checks, most returning empty arrays.
> Transition to SSE reduces backend load by orders of magnitude while decreasing
> notification latency from 60 seconds to sub-200 milliseconds."

**How we do it:**
- Per-user `asyncio.Queue` registry (one queue per connected browser tab)
- Client connects once via `GET /api/events/stream` → persistent SSE connection
- Server pushes events only when there's actual data:
  - `meeting_alert` — new meeting invitation detected
  - `email_processed` — email finished AI processing
  - `sync_complete` — Gmail sync finished
- 30-second keep-alive heartbeats prevent connection timeout
- Automatic cleanup on client disconnect
- Initial state push on connect (pending alerts, unread count)

**API Endpoints:**
- `GET  /api/events/stream` — SSE stream (persistent connection)
- `GET  /api/events/status` — Connection monitoring stats

---

## FEATURE 11 — Passive Tone Learning *(Superhuman Architecture Fix)*

| Detail        | Value |
|---------------|-------|
| **Status**    | ✅ BUILT |
| **File**      | `services/tone_learning_service.py` |
| **Routes**    | `/api/tone/*` |

**What it does:**
Replaces the static "tone profile" string with a passive, evolving AI-learned stylistic profile.

**Why (from Superhuman analysis):**
> "Superhuman continuously and passively scans the user's outbox, analyzing emotional cues,
> formality gradients, and syntactical clarity without requiring explicit user feedback.
> The system literally learns by observing the user write."

**How we do it:**
- On first login: scans last 25 sent emails from Gmail API
- AI extracts **12 stylistic dimensions**:
  - Formality level (casual → very formal)
  - Greeting & sign-off style ("Hey" vs "Dear Sir")
  - Sentence length, vocabulary complexity
  - Exclamation marks, emoji usage
  - Directness, humor level
  - Key phrases the user frequently uses
  - Overall personality summary
- Profile stored in MongoDB `users.tone_profile` as rich JSON
- **Auto-refreshes every 7 days** to evolve with the user
- Used by all reply generation (regular + meeting + nudge)

**API Endpoints:**
- `POST /api/tone/learn` — Trigger tone learning from sent emails
- `GET  /api/tone/profile` — View current learned profile
- `POST /api/tone/refresh` — Refresh if stale (>7 days)

---

## BACKEND FILE MAP (41 Python files)

```
backend/
├── .env.example                             # All env vars documented
├── .gitignore
├── requirements.txt                         # 20 dependencies
│
└── app/
    ├── main.py                              # FastAPI app + lifecycle + 9 route groups
    │
    ├── core/
    │   ├── config.py                        # Pydantic settings (env loading)
    │   ├── database.py                      # Motor MongoDB + 10 index definitions
    │   └── security.py                      # AES-256-GCM + JWT
    │
    ├── models/
    │   └── schemas.py                       # 20+ Pydantic models + 7 enums
    │
    ├── services/
    │   ├── auth_service.py                  # Google OAuth flow
    │   ├── gmail_service.py                 # Email sync + send
    │   ├── meeting_service.py               # Accept/Decline/Suggest + Calendar
    │   ├── analytics_service.py             # 6 analytics queries
    │   ├── unsubscribe_service.py           # Bulk unsubscriber
    │   ├── reply_tracker_service.py         # Reply Zero tracking
    │   ├── cold_email_service.py            # Cold email blocker
    │   ├── sse_service.py                   # Real-time SSE push (Superhuman fix)
    │   └── tone_learning_service.py         # Passive tone learning (Superhuman fix)
    │
    ├── ai_worker/
    │   ├── ai_provider.py                   # Groq/OpenAI abstraction
    │   ├── pipeline.py                      # 6-task orchestrator + SSE push + Inbox Zero checks
    │   └── tasks/
    │       ├── classify.py                  # Task 1: 8-category classifier
    │       ├── meeting_intelligence.py      # Task 2: Calendar + availability
    │       ├── summarise.py                 # Task 3: Smart summary
    │       ├── extract_actions.py           # Task 4: Action items
    │       ├── risk_detect.py               # Task 5: Phishing detection
    │       └── reply_draft.py               # Task 6: On-demand for meetings (Superhuman fix)
    │
    └── routes/
        ├── middleware.py                    # JWT auth dependency
        ├── auth_routes.py                   # 3 endpoints
        ├── gmail_routes.py                  # 4 endpoints
        ├── meeting_routes.py                # 6 endpoints
        ├── analytics_routes.py              # 6 endpoints
        ├── unsubscribe_routes.py            # 4 endpoints
        ├── reply_tracker_routes.py          # 6 endpoints
        ├── cold_email_routes.py             # 4 endpoints
        ├── sse_routes.py                    # 2 endpoints (Superhuman fix)
        └── tone_routes.py                   # 3 endpoints (Superhuman fix)
```

**Total API Endpoints: 38**
**Total MongoDB Collections: 8** (users, emails, google_tokens, meeting_alerts, email_threads, unsubscribe_preferences, cold_email_settings, sender_whitelist)
**Total MongoDB Indexes: 10**

---

## BACKEND STATUS — What's Remaining

| Task | Status | Notes |
|------|--------|-------|
| Core config + env | ✅ Done | Pydantic settings |
| MongoDB + indexes | ✅ Done | 10 indexes across 8 collections |
| AES-256 encryption | ✅ Done | Token storage |
| JWT auth | ✅ Done | Middleware + token flow |
| Google OAuth flow | ✅ Done | Single consent, T&C |
| Gmail sync + parse | ✅ Done | Full message parsing |
| 6-task AI pipeline | ✅ Done | All 6 tasks |
| Meeting Intelligence | ✅ Done | 5-stage engine |
| Meeting responses | ✅ Done | Accept/Decline/Suggest (on-demand drafts) |
| Calendar integration | ✅ Done | Events + availability |
| Bulk Unsubscriber | ✅ Done | Newsletter cleaning |
| Cold Email Blocker | ✅ Done | AI-powered detection |
| Reply Zero Tracker | ✅ Done | Nudge + tracking |
| Email Analytics | ✅ Done | 6 query types |
| SSE Real-Time Push | ✅ Done | Replaces 60s polling (Superhuman fix) |
| Passive Tone Learning | ✅ Done | 12-dimension stylistic profile (Superhuman fix) |
| On-Demand Meeting Drafts | ✅ Done | Fixes pre-computation paradox (Superhuman fix) |
| **Background Worker** | ✅ Done | Added APScheduler for auto-sync and processing |
| **Rate Limiting** | ✅ Done | Included slowapi for API rate limiting |
| **Tests** | ✅ Done | Setup Pytest framework and configured endpoint testing |

---

## SUPERHUMAN-INSPIRED ARCHITECTURE CHANGES LOG

| Gap Identified | Old Approach | New Approach | File Changed |
|---------------|-------------|--------------|--------------|
| Polling bottleneck at scale | 60s polling `/gmail/status` | SSE persistent push via `/events/stream` | `sse_service.py` (new) |
| Pre-computation waste | Pre-generate accept + decline for ALL meetings | Generate on-demand only when user clicks | `pipeline.py` (refactored) |
| Static tone profile | Hardcoded string in DB | Passive learning from 25 sent emails, 12 dimensions, auto-refresh weekly | `tone_learning_service.py` (new) |

---

## FRONTEND PLAN (Phase 2)

**Stack:** React + Vite
**Design:** Apple-style Glassmorphism (frosted glass, blur, depth, subtle shadows)

> 📝 **Design Direction**: Clean, premium feel inspired by Apple's website.
> Frosted glass panels (`backdrop-filter: blur()`), depth layering with subtle shadows,
> smooth spring transitions, SF Pro / Inter typography, dark mode default with
> light mode toggle. Every surface should feel like frosted glass floating above
> a soft gradient background.

*(Frontend dashboard, split inbox view, Apple-style UI, layout, and analytics charts have been successfully built and connected.)*

