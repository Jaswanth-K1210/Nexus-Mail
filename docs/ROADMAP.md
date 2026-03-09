# Nexus Mail — Master Roadmap
## The Best of Superhuman + Inbox Zero + Our Own Innovation
### March 6, 2026

---

## Philosophy

We take the **best architectural patterns** from both Superhuman and Inbox Zero, 
combine them, and then build features **neither platform has**.

| Source | What We Take | What We Skip |
|--------|-------------|--------------|
| **Superhuman** | Zero-loss modifier pattern, passive vector tone matching, behavioral classification | WebSQL local-first (too complex for our stack), $30/mo pricing wall |
| **Inbox Zero** | historyId cursor sync, Pydantic validation + retry, email sanitization, draft-first safety, natural language rules | PostgreSQL + Prisma (we keep MongoDB), Tinybird (overkill for us), Next.js Server Actions |
| **Nexus Original** | Meeting Intelligence engine, SSE push, 6-task AI pipeline | Old polling sync, static tone profiles |

---

## Complete Feature Map: What We Have vs. What We're Adding

### ✅ ALREADY BUILT (Backend Complete)

| # | Feature | Origin | Status |
|---|---------|--------|--------|
| 1 | Google OAuth + Single Consent | v3.1 Spec | ✅ Done |
| 2 | Gmail Sync (historyId cursor) | Inbox Zero fix | ✅ Done |
| 3 | 6-Task AI Pipeline + Sanitizer | v3.1 + Inbox Zero fix | ✅ Done |
| 4 | Meeting Intelligence (5-stage) | Nexus Original | ✅ Done |
| 5 | Accept/Decline/Suggest (on-demand drafts) | Superhuman fix | ✅ Done |
| 6 | Bulk Unsubscriber | Inbox Zero | ✅ Done |
| 7 | Cold Email Blocker | Inbox Zero | ✅ Done |
| 8 | Reply Zero Tracker + Nudge | Inbox Zero | ✅ Done |
| 9 | Email Analytics (6 queries) | Inbox Zero | ✅ Done |
| 10 | SSE Real-Time Push | Superhuman fix | ✅ Done |
| 11 | Passive Tone Learning (12 dimensions) | Superhuman fix | ✅ Done |
| 12 | Pydantic AI Validation + Retry | Inbox Zero fix | ✅ Done |
| 13 | Email Body Sanitizer | Inbox Zero fix | ✅ Done |
| 14 | AES-256-GCM + JWT Security | v3.1 Spec | ✅ Done |

### 🔨 NEW FEATURES TO BUILD (Backend Phase 2)

| # | Feature | Inspired By | Why It's Better |
|---|---------|-------------|-----------------|
| 15 | **Draft-First Mode** | Inbox Zero | AI generates but never auto-sends. User previews + confirms. Configurable per-rule confidence threshold for auto-send. |
| 16 | **Natural Language Rules** | Inbox Zero | Users write rules like "emails from @company.com get labeled VIP". LLM interprets semantically, not via string matching. But we ADD meeting-awareness and action chaining. |
| 17 | **Smart Priority Scoring** | Superhuman | Every email gets a 0-100 priority score based on sender relationship strength, reply velocity, and content urgency. Powers a Split Inbox. |
| 18 | **Thread Summarization** | Neither has this | Summarize entire email threads (not just individual emails). When a thread has 15 back-and-forth messages, get the full context in 3 sentences. |
| 19 | **Sender Intelligence** | Both combined | Per-sender profile: relationship strength, response time, email frequency, read rate, cold email risk. Powers smart classification. |
| 20 | **Redis Distributed Locking** | Inbox Zero | Prevent race conditions during concurrent sync/processing. Critical for production. |
| 21 | **Webhook Ingestion (Pub/Sub)** | Inbox Zero | Real-time Gmail push notifications instead of manual sync triggers. Emails arrive instantly. |

---

## BUILD ROADMAP

### Phase 1: Safety + Rules Engine (Backend)
> **Goal**: Make the AI trustworthy enough for production use

#### 1.1 — Draft-First Mode
**Why**: This is the #1 trust barrier. Users won't let AI send emails without reviewing them first. Inbox Zero defaults to this. Superhuman doesn't auto-send either.

**How we do it BETTER**: Confidence-based auto-send. Instead of rigid "always draft" or "always send", we introduce a confidence threshold per rule.

```
File: services/draft_service.py
New collection: email_drafts
Fields: user_id, email_id, draft_body, draft_type (reply/forward), 
        ai_confidence, status (pending/approved/rejected/auto_sent),
        auto_send_threshold, created_at, reviewed_at
```

**Logic**:
- Default mode: ALL AI-generated replies stored as drafts → user previews → clicks "Send"
- Power user mode: If `ai_confidence >= user.auto_send_threshold` (default 0.95) AND rule has `auto_send: true`, auto-dispatch
- Meeting Accept/Decline: Currently auto-sends → change to draft-first by default
- Frontend shows a "Pending Drafts" sidebar with approve/reject/edit

**Endpoints**:
- `GET  /api/drafts` — List pending drafts
- `POST /api/drafts/{id}/approve` — Approve and send
- `POST /api/drafts/{id}/reject` — Reject and discard
- `PUT  /api/drafts/{id}/edit` — Edit before sending
- `PUT  /api/settings/auto-send` — Configure auto-send threshold

---

#### 1.2 — Natural Language Rules Engine
**Why**: Inbox Zero's killer feature. Users define behavior in plain English instead of clicking through filter menus. Gmail's static filters are fundamentally broken for modern email.

**How we do it BETTER**: We add **action chaining** and **meeting awareness** that Inbox Zero doesn't have.

```
File: services/rules_engine.py
New collection: user_rules
Fields: user_id, rule_text (natural language), compiled_actions[], 
        is_active, match_count, last_matched, created_at
```

**Example rules users can write**:
- "Emails from investors or board members → label VIP + mark priority 100"
- "Newsletters I haven't read in 30 days → auto-archive"
- "Meeting invitations from @company.com → auto-accept if I'm free"
- "Sales pitches → archive + apply Cold Email label"
- "Emails marked urgent that mention deadlines → notify immediately via SSE"

**How the LLM compiles rules**:
1. User writes natural language rule
2. LLM converts to structured action JSON:
```json
{
  "conditions": {"sender_domain": "company.com", "is_meeting": true},
  "actions": [
    {"type": "check_availability"},
    {"type": "auto_accept_if_free"},
    {"type": "label", "value": "Auto-Accepted"}
  ],
  "confidence_threshold": 0.85
}
```
3. Pydantic validates the JSON (using our retry logic)
4. Rule is stored and evaluated during pipeline processing

**Endpoints**:
- `POST /api/rules` — Create rule (natural language input)
- `GET  /api/rules` — List active rules
- `PUT  /api/rules/{id}` — Update rule
- `DELETE /api/rules/{id}` — Delete rule
- `POST /api/rules/test` — Test a rule against sample emails

---

### Phase 2: Intelligence Layer (Backend)
> **Goal**: Make Nexus smarter than both Superhuman and Inbox Zero

#### 2.1 — Smart Priority Scoring
**Why**: Superhuman uses "communication velocity" to sort emails. Inbox Zero uses LLM classification. We combine BOTH into a single priority score.

**How we do it BETTER**: Multi-signal scoring that neither platform fully implements.

```
File: services/priority_service.py
```

**Scoring Algorithm (0-100)**:
| Signal | Weight | How Calculated |
|--------|--------|---------------|
| Sender Relationship | 30% | Reply frequency, response time, thread count with this sender |
| Content Urgency | 25% | AI detects deadlines, "ASAP", time-sensitive language |
| Category Weight | 20% | important=90, requires_response=80, meeting=85, newsletter=10 |
| Recency Decay | 15% | Exponential decay as email ages (fresh = high) |
| User Behavior | 10% | How fast user typically opens emails from this sender |

**Output**: Every email gets `priority_score: 0-100` stored in MongoDB.
**Frontend use**: Split inbox sorted by priority (not chronology).

---

#### 2.2 — Thread Summarization
**Why**: Neither Superhuman nor Inbox Zero summarizes entire threads. They only summarize single emails. When a thread has 15 messages, you still have to scroll through all of them.

**How we do it**:
```
File: services/thread_service.py
```

- Group emails by `thread_id`
- When user opens a thread, concatenate all messages chronologically
- AI generates: 
  - **Thread summary** (3-5 sentences covering all back-and-forth)
  - **Key decisions made** (what was agreed)
  - **Open questions** (what's still unresolved)
  - **Action items per participant** (who owes what)
- Cache in `email_threads` collection

**Endpoints**:
- `GET /api/threads/{thread_id}/summary` — Get/generate thread summary
- `GET /api/threads` — List threads with previews

---

#### 2.3 — Sender Intelligence Profiles
**Why**: Superhuman tracks "communication velocity" per sender. Inbox Zero's cold email blocker checks sender history. We build a complete sender profile combining both approaches.

```
File: services/sender_intelligence.py
New collection: sender_profiles
```

**Per-sender profile**:
```json
{
  "sender_email": "john@company.com",
  "sender_name": "John Smith",
  "relationship_strength": 0.85,
  "total_emails": 47,
  "total_replies": 23,
  "avg_response_time_hours": 2.3,
  "first_contact": "2025-06-15",
  "last_contact": "2026-03-05",
  "categories": {"important": 12, "meeting_invitation": 8, "requires_response": 15},
  "is_cold_sender": false,
  "is_vip": true,
  "organization": "Company Inc.",
  "read_rate": 0.92
}
```

**Powers**:
- Smart priority scoring (sender relationship signal)
- Cold email detection (first-contact check is instant, not a DB query each time)
- Unsubscribe recommendations ("You read 3% of this sender's emails")
- VIP detection (auto-label high-interaction senders)

**Endpoint**:
- `GET /api/senders` — List sender profiles with stats
- `GET /api/senders/{email}` — Single sender profile

---

### Phase 3: Production Hardening (Backend)
> **Goal**: Make it safe for real users at scale

#### 3.1 — Redis Distributed Locking
**Why**: Inbox Zero uses Redis locks to prevent race conditions when multiple webhooks arrive simultaneously. Without this, concurrent syncs can duplicate emails or corrupt state.

```
File: core/redis_client.py
Dependency: redis[hiredis] (add to requirements.txt)
```

**Where locks are needed**:
- `gmail_service.sync_emails()` — Lock per user during sync
- `pipeline.process_email()` — Lock per email during processing
- `meeting_service.accept_meeting()` — Lock per alert during response

**Pattern**:
```python
async with redis_lock(f"sync:{user_id}", timeout=60):
    await self._incremental_sync(...)
```

---

#### 3.2 — Gmail Pub/Sub Webhook
**Why**: Currently the user must manually trigger `/api/gmail/sync`. Inbox Zero uses Google Cloud Pub/Sub to receive instant push notifications when new emails arrive.

```
File: routes/webhook_routes.py
```

**How**:
1. On OAuth connect: call `gmail.users().watch()` to register our webhook URL
2. Google pushes to `/api/webhooks/gmail` when inbox changes
3. Webhook triggers `_incremental_sync()` (using our historyId cursor)
4. Result: emails arrive in Nexus within ~2 seconds of hitting Gmail

---

#### 3.3 — Rate Limiting
```
File: routes/rate_limiter.py
```
- Redis-backed sliding window per user per endpoint
- Default: 60 requests/minute for standard endpoints
- AI endpoints (process, nudge, rules/test): 10 requests/minute
- SSE: 2 connections per user max

---

### Phase 4: Frontend (React + Apple Glassmorphism)
> **Goal**: A visual experience that makes Superhuman look dated

**Stack**: React + Vite
**Design**: Apple-inspired glassmorphism (frosted glass, blur, depth layering)
**Typography**: Inter / SF Pro
**Theme**: Dark mode default, light mode toggle

#### 4.1 — Core Pages
| Page | Key Components |
|------|---------------|
| **Login** | Google OAuth button on frosted glass card |
| **Dashboard** | Glass stat cards (unread, pending, priority), volume chart, category donut |
| **Inbox** | Split view: priority-sorted list (left) + email detail (right), glass panels |
| **Email Detail** | AI summary card, action items, risk flags, reply draft with approve/edit |
| **Meeting Alerts** | Traffic light cards (green/amber/red), Accept/Decline glass buttons |
| **Analytics** | Full-screen charts: volume timeline, sender treemap, hourly heatmap |
| **Unsubscribe Manager** | Sender list with read % bars, one-click actions |
| **Reply Tracker** | Two-column: To Reply (left) + Awaiting Reply (right) |
| **Settings** | Rules editor, cold email config, auto-send threshold, tone profile display |

#### 4.2 — Design System
```css
/* Core glass tokens */
--glass-bg: rgba(255, 255, 255, 0.08);
--glass-border: rgba(255, 255, 255, 0.12);
--glass-blur: blur(20px);
--shadow-depth-1: 0 4px 30px rgba(0, 0, 0, 0.15);
--shadow-depth-2: 0 8px 60px rgba(0, 0, 0, 0.25);

/* Every surface */
.glass-panel {
  background: var(--glass-bg);
  backdrop-filter: var(--glass-blur);
  border: 1px solid var(--glass-border);
  border-radius: 16px;
  box-shadow: var(--shadow-depth-1);
}
```

#### 4.3 — Animations
- Page transitions: Framer Motion spring physics
- Card hover: subtle scale(1.02) + shadow elevation
- Email list: staggered fade-in on load
- Meeting alert: pulse animation on new alerts
- Chart rendering: animated draw-in on mount

---

## BUILD ORDER (Estimated Timeline)

```
PHASE 1: Safety + Rules (Backend)
├── 1.1 Draft-First Mode ......................... 2-3 hours
├── 1.2 Natural Language Rules Engine ............ 3-4 hours
└── Total ........................................ ~7 hours

PHASE 2: Intelligence Layer (Backend)
├── 2.1 Smart Priority Scoring ................... 2 hours
├── 2.2 Thread Summarization ..................... 2 hours
├── 2.3 Sender Intelligence Profiles ............. 2 hours
└── Total ........................................ ~6 hours

PHASE 3: Production Hardening (Backend)
├── 3.1 Redis Distributed Locking ................ 1 hour
├── 3.2 Gmail Pub/Sub Webhook .................... 2 hours
├── 3.3 Rate Limiting ............................ 1 hour
└── Total ........................................ ~4 hours

PHASE 4: Frontend (React)
├── 4.1 Project Setup + Design System ............ 2 hours
├── 4.2 Auth + Dashboard ......................... 3 hours
├── 4.3 Inbox + Email Detail ..................... 4 hours
├── 4.4 Meeting Intelligence UI .................. 3 hours
├── 4.5 Analytics + Unsubscribe + Reply Tracker .. 4 hours
├── 4.6 Settings + Rules Editor .................. 2 hours
├── 4.7 Polish + Animations ...................... 2 hours
└── Total ........................................ ~20 hours
```

**Grand Total: ~37 hours of development**

---

## WHAT MAKES US BETTER THAN BOTH

| Capability | Superhuman | Inbox Zero | **Nexus Mail** |
|-----------|-----------|-----------|---------------|
| Meeting Intelligence | ❌ None | ❌ None | ✅ **5-stage engine + calendar + one-click response** |
| Draft Safety | ⚠️ Manual send | ✅ Always draft | ✅ **Confidence-based auto-send** (smarter) |
| Tone Matching | ✅ Vector embeddings | ⚠️ Few-shot examples | ✅ **12-dimension passive learning + auto-refresh** |
| Rule Engine | ❌ Manual splits only | ✅ Natural language | ✅ **NL rules + meeting awareness + action chaining** |
| Cold Email Blocking | ❌ None | ✅ LLM-based | ✅ **LLM + pipeline pre-filter (saves AI costs)** |
| Email Sync | ✅ Modifier queue | ✅ historyId cursor | ✅ **historyId + SSE push (best of both)** |
| Priority Scoring | ⚠️ Behavioral velocity | ⚠️ LLM classification | ✅ **5-signal algorithm (both combined)** |
| Thread Summary | ❌ None | ❌ None | ✅ **Full thread context + decisions + open questions** |
| Sender Intelligence | ⚠️ Basic velocity | ⚠️ Cold check only | ✅ **Complete profile with relationship strength** |
| Analytics | ❌ None | ✅ Tinybird | ✅ **6 query types, no extra infra needed** |
| Real-Time Notifications | ✅ Browser extension | ⚠️ Webhook only | ✅ **SSE push (lighter than extension)** |
| Pricing | ❌ $30/month | ✅ Free/open-source | ✅ **Free + self-hostable** |
| Validation | N/A | ✅ Zod + retry | ✅ **Pydantic + retry (same pattern)** |
| Token Optimization | N/A | ✅ Sanitizer | ✅ **Sanitizer (same pattern)** |
| Deployment Complexity | ❌ Massive | ⚠️ 5-service stack | ✅ **FastAPI + MongoDB (2 services)** |

**Our unique combination**: Meeting Intelligence + Draft-First Safety + Natural Language Rules + Thread Summarization + Sender Intelligence + Priority Scoring. No existing product has all six together.

---

## RECOMMENDED NEXT STEP

Start with **Phase 1.1 (Draft-First Mode)** — it's the most critical trust feature 
and the foundation for the rules engine. Should we begin building?
