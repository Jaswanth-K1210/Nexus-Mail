# Superhuman vs Nexus Mail — Architectural Analysis

> Research performed by the project author. This document informs backend architecture decisions.

## Key Architectural Gaps Identified

### 1. Polling → SSE (CRITICAL)
- Current: Chrome Extension polls `/gmail/status` every 60 seconds
- Problem: 100K users = 100K requests/minute, most returning empty arrays
- Fix: Server-Sent Events (SSE) for real-time push notifications

### 2. Pre-Computation Paradox (HIGH)
- Current: `reply_draft.py` pre-computes BOTH accept+decline drafts for every meeting
- Problem: 20 meetings/day × 15 dismissed = 30 wasted LLM calls
- Fix: Generate drafts on-demand when user clicks Accept/Decline

### 3. Tone Profile — Static vs Passive Learning (MEDIUM)
- Current: Static tone profile string in user document
- Superhuman: Continuous passive vector embedding learning from outbox
- Fix: Build a tone learning service that analyzes sent emails

## Full Analysis
(See the complete research document for the detailed reverse-engineering of Superhuman's
Local-First Sync Engine, Modifier Queue pattern, Multi-Agent Cognitive Array,
Vector Embedding tone matching, and in-browser SQL compiler architecture.)
