# Nexus Mail: Enterprise SaaS Scalability Architecture
*Version: 1.0 (B2B / SaaS Optimization)*

To transition Nexus Mail from a single-user prototype to a globally scalable, multi-tenant B2B SaaS product, we have designed a robust, tenant-isolated architecture. This blueprint defines how data, billing, and teams are structured to support thousands of concurrent users and companies while maintaining strict data privacy protocols.

---

## 1. Multi-Tenant Database Schema

Nexus Mail utilizes **Logical Isolation** via MongoDB, meaning all data resides in shared collections but is strictly partitioned by `workspace_id` and `user_id`.

### Core Entities & Scaling Schema:

#### `workspaces` (B2B Teams / Organizations)
Instead of tying billing to individuals, billing is tied to a Workspace. 
*   `_id`: Object ID
*   `name`: "Acme Corp"
*   `domain`: "acme.com" (Auto-joins users from this domain)
*   `owner_id`: Ref(User)
*   `subscription_tier`: "Free" | "Pro" | "Enterprise"
*   `stripe_customer_id`: "cus_XXXXXXXXX"
*   `billing_status`: "active" | "past_due" | "canceled"
*   `max_users`: int
*   `created_at`: datetime

#### `users` (Appended SaaS Fields)
*   `workspace_id`: Ref(Workspace) — Links the user to their corporate team.
*   `role`: "admin" | "member"
*   `onboarding_completed`: boolean

#### `subscriptions` (Billing Engine)
*   `_id`: Object ID
*   `workspace_id`: Ref(Workspace) 
*   `stripe_subscription_id`: "sub_XXXXXXX"
*   `plan_id`: "price_XXXXXX"
*   `current_period_end`: datetime
*   `cancel_at_period_end`: boolean

---

## 2. Subscription Tiers & Feature Gating

Feature access is dynamically governed by the Workspace's `subscription_tier`.

### Tier 1: Free (Individual)
*   **Limit:** 1 User
*   **Sync Limit:** 500 emails / week
*   **AI Access:** Groq / Llama-3 only. Summaries & basic classification.
*   **Meeting Engine:** Disabled.

### Tier 2: Pro ($15 / mo)
*   **Limit:** 1 User
*   **Sync Limit:** Unlimited
*   **AI Access:** Enhanced Priority Engine, Calendar Intelligence, Draft-First Replies.
*   **Timeline:** Full Mail Specialist Timeline integration.

### Tier 3: Teams / Enterprise ($12 / mo per seat)
*   **Limit:** 5+ Users
*   **Feature:** Centralized billing, Team Admin Dashboard.
*   **Feature:** Shared "Rules" inside the natural language processing engine (e.g. "Archive all emails from typical competitor domains").
*   **Security:** Enforced Google Workspace SSO login.

---

## 3. Rate Limiting & Background Job Scaling

Currently, `APScheduler` runs background sync tasks in Python memory. To scale:
1.  **Celery + Redis:** Move off `APScheduler` directly into a heavily parallelized `Celery` fleet backed by Redis Streams.
2.  **Tiered Queues & Sync Intervals:**
    *   **Tier 1 (Free):** Polling loop runs every 15 minutes to batch-fetch new emails. This minimizes compute overhead.
    *   **Tier 2 & 3 (Pro & Enterprise):** Real-time Google Pub/Sub Webhook Sync. 
3.  **Webhook Sync (Pro/Enterprise Only):** Instead of manual polling, we subscribe to Google's `watch()` push notifications via Cloud Pub/Sub. The exact moment an email hits the user's Gmail, Google fires a webhook to Nexus Mail. This instantly wakes up a Celery worker to perform real-time, zero-latency processing of the incoming email.

---

## 4. Security & Compliance Protocol
*   **SOC 2 Readiness:** All OAuth tokens (`google_tokens` collection) are symmetrically encrypted at rest using AES-256-GCM before database insertion. The decryption key resides exclusively injected at runtime via Kubernetes Secrets.
*   **Zero-Data Retention:** For Enterprise clients, the AI processing pipeline only scores and categorizes emails, but the actual `body_text` and `body_html` are continuously purged using MongoDB TTL (Time-To-Live) indexes extending no more than 7 days.
