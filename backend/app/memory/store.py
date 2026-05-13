"""
Nexus Mail — Memory System

Multi-tier memory architecture for agents:
- Short-term: Redis-backed session context (current workflow state)
- Long-term: MongoDB-backed persistent memory (sender profiles, preferences)
- Episodic: MongoDB-backed past decisions (how we handled similar emails)
- Semantic: MongoDB-backed compressed thread summaries

Inspired by MemGPT, AutoGen memory, and production RAG systems.
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)


# ─── Short-Term Memory (Redis) ───────────────────────────────────────────────

class ShortTermMemory:
    """
    Redis-backed session memory for current workflow context.
    Fast reads/writes, auto-expires after session ends.
    """

    def __init__(self, ttl_seconds: int = 3600):
        self.ttl = ttl_seconds

    async def store(self, key: str, value: Any) -> None:
        """Store a value in short-term memory."""
        try:
            from app.core.redis_client import get_redis
            redis = get_redis()
            serialized = json.dumps(value, default=str)
            await redis.set(f"stm:{key}", serialized, ex=self.ttl)
        except Exception as e:
            logger.debug("Short-term memory store failed", key=key, error=str(e))

    async def recall(self, key: str) -> Any:
        """Recall a value from short-term memory."""
        try:
            from app.core.redis_client import get_redis
            redis = get_redis()
            value = await redis.get(f"stm:{key}")
            return json.loads(value) if value else None
        except Exception as e:
            logger.debug("Short-term memory recall failed", key=key, error=str(e))
            return None

    async def delete(self, key: str) -> None:
        """Delete a value from short-term memory."""
        try:
            from app.core.redis_client import get_redis
            redis = get_redis()
            await redis.delete(f"stm:{key}")
        except Exception:
            pass


# ─── Long-Term Memory (MongoDB) ──────────────────────────────────────────────

class LongTermMemory:
    """
    MongoDB-backed persistent memory for sender relationships,
    user preferences, and VIP lists.
    """

    async def store_sender_memory(
        self,
        user_id: str,
        sender_email: str,
        memory_type: str,
        data: dict,
    ) -> None:
        """Store or update a sender-related memory."""
        try:
            from app.core.database import get_database
            db = get_database()
            await db.agent_memory.update_one(
                {
                    "user_id": user_id,
                    "sender_email": sender_email,
                    "memory_type": memory_type,
                },
                {
                    "$set": {
                        "data": data,
                        "updated_at": datetime.now(timezone.utc),
                    },
                    "$setOnInsert": {
                        "created_at": datetime.now(timezone.utc),
                    },
                },
                upsert=True,
            )
        except Exception as e:
            logger.warning("Long-term memory store failed", error=str(e))

    async def recall_sender_memory(
        self,
        user_id: str,
        sender_email: str,
        memory_type: str | None = None,
    ) -> list[dict]:
        """Recall all memories about a sender."""
        try:
            from app.core.database import get_database
            db = get_database()

            query: dict = {"user_id": user_id, "sender_email": sender_email}
            if memory_type:
                query["memory_type"] = memory_type

            cursor = db.agent_memory.find(
                query, {"_id": 0}
            ).sort("updated_at", -1)

            return await cursor.to_list(length=20)
        except Exception as e:
            logger.warning("Long-term memory recall failed", error=str(e))
            return []

    async def store_user_preference(
        self,
        user_id: str,
        preference_key: str,
        value: Any,
    ) -> None:
        """Store a user preference learned from behavior."""
        try:
            from app.core.database import get_database
            db = get_database()
            await db.agent_memory.update_one(
                {
                    "user_id": user_id,
                    "memory_type": "user_preference",
                    "data.key": preference_key,
                },
                {
                    "$set": {
                        "data": {"key": preference_key, "value": value},
                        "updated_at": datetime.now(timezone.utc),
                    },
                    "$setOnInsert": {
                        "created_at": datetime.now(timezone.utc),
                    },
                },
                upsert=True,
            )
        except Exception as e:
            logger.warning("Preference store failed", error=str(e))


# ─── Episodic Memory (MongoDB) ───────────────────────────────────────────────

class EpisodicMemory:
    """
    MongoDB-backed episodic memory for past agent decisions.
    Enables agents to recall "how did I handle a similar email from this sender?"
    """

    async def store_episode(
        self,
        user_id: str,
        email_id: str,
        sender_email: str,
        agent_name: str,
        decision: str,
        outcome: dict,
    ) -> None:
        """Store an episode (agent decision + outcome) for future recall."""
        try:
            from app.core.database import get_database
            db = get_database()
            await db.agent_episodes.insert_one({
                "user_id": user_id,
                "email_id": email_id,
                "sender_email": sender_email,
                "agent": agent_name,
                "decision": decision,
                "outcome": outcome,
                "timestamp": datetime.now(timezone.utc),
            })
        except Exception as e:
            logger.warning("Episode store failed", error=str(e))

    async def recall_similar_episodes(
        self,
        user_id: str,
        sender_email: str | None = None,
        agent_name: str | None = None,
        limit: int = 5,
    ) -> list[dict]:
        """Recall past episodes for a sender or agent."""
        try:
            from app.core.database import get_database
            db = get_database()

            query: dict = {"user_id": user_id}
            if sender_email:
                query["sender_email"] = sender_email
            if agent_name:
                query["agent"] = agent_name

            cursor = db.agent_episodes.find(
                query, {"_id": 0}
            ).sort("timestamp", -1).limit(limit)

            return await cursor.to_list(length=limit)
        except Exception as e:
            logger.warning("Episode recall failed", error=str(e))
            return []


# ─── Semantic Memory (MongoDB) ───────────────────────────────────────────────

class SemanticMemory:
    """
    MongoDB-backed semantic memory for compressed thread summaries.
    Provides agents with conversation context without loading full threads.
    Optional: can be extended with vector DB (Qdrant, Pinecone) for similarity search.
    """

    async def store_thread_summary(
        self,
        user_id: str,
        thread_id: str,
        summary: str,
        key_topics: list[str] | None = None,
        participants: list[str] | None = None,
    ) -> None:
        """Store a compressed thread summary."""
        try:
            from app.core.database import get_database
            db = get_database()
            await db.thread_summaries.update_one(
                {"user_id": user_id, "thread_id": thread_id},
                {
                    "$set": {
                        "summary": summary,
                        "key_topics": key_topics or [],
                        "participants": participants or [],
                        "updated_at": datetime.now(timezone.utc),
                    },
                    "$setOnInsert": {
                        "created_at": datetime.now(timezone.utc),
                    },
                },
                upsert=True,
            )
        except Exception as e:
            logger.warning("Thread summary store failed", error=str(e))

    async def recall_thread_summary(
        self,
        user_id: str,
        thread_id: str,
    ) -> dict | None:
        """Recall a thread summary."""
        try:
            from app.core.database import get_database
            db = get_database()
            doc = await db.thread_summaries.find_one(
                {"user_id": user_id, "thread_id": thread_id},
                {"_id": 0},
            )
            return doc
        except Exception as e:
            logger.warning("Thread summary recall failed", error=str(e))
            return None


# ─── Unified Memory Store ────────────────────────────────────────────────────

class MemoryStore:
    """
    Unified memory interface for agents.
    Provides access to all memory tiers through a single interface.

    Usage:
        memory = MemoryStore()
        await memory.short_term.store("current_email", email_data)
        sender_memories = await memory.long_term.recall_sender_memory(user_id, sender)
        past_decisions = await memory.episodic.recall_similar_episodes(user_id, sender)
    """

    def __init__(self):
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory()

    async def load_context_for_email(
        self,
        user_id: str,
        sender_email: str,
        thread_id: str | None = None,
    ) -> dict:
        """
        Pre-load all relevant memory context for email processing.
        Called by the orchestrator before agents execute.
        """
        context: dict = {
            "sender_memories": [],
            "past_episodes": [],
            "thread_summary": None,
            "user_preferences": [],
        }

        # Long-term sender memory
        context["sender_memories"] = await self.long_term.recall_sender_memory(
            user_id, sender_email
        )

        # Past episodes with this sender
        context["past_episodes"] = await self.episodic.recall_similar_episodes(
            user_id, sender_email=sender_email, limit=3
        )

        # Thread summary if available
        if thread_id:
            context["thread_summary"] = await self.semantic.recall_thread_summary(
                user_id, thread_id
            )

        return context

    async def persist_workflow_results(
        self,
        user_id: str,
        email_id: str,
        sender_email: str,
        thread_id: str,
        agent_results: dict,
        workflow_summary: str = "",
    ) -> None:
        """
        Persist all relevant data from a completed workflow into long-term memory.
        Called by the orchestrator after all agents complete.
        """
        # Store sender interaction
        await self.long_term.store_sender_memory(
            user_id=user_id,
            sender_email=sender_email,
            memory_type="interaction",
            data={
                "email_id": email_id,
                "agents_involved": list(agent_results.keys()),
                "category": agent_results.get("triage_agent", {}).get("category"),
                "priority": agent_results.get("triage_agent", {}).get("priority_score"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        # Store episodes for each agent
        for agent_name, result in agent_results.items():
            decision = result.get("_decision", "")
            if decision:
                await self.episodic.store_episode(
                    user_id=user_id,
                    email_id=email_id,
                    sender_email=sender_email,
                    agent_name=agent_name,
                    decision=decision,
                    outcome=result,
                )

        # Store/update thread summary if we generated a new summary
        triage_output = agent_results.get("triage_agent", {})
        summary = triage_output.get("summary", workflow_summary)
        if summary and thread_id:
            await self.semantic.store_thread_summary(
                user_id=user_id,
                thread_id=thread_id,
                summary=summary,
                participants=[sender_email],
            )


# ─── Singleton ────────────────────────────────────────────────────────────────

_memory_store: MemoryStore | None = None


def get_memory_store() -> MemoryStore:
    """Get or create the global memory store singleton."""
    global _memory_store
    if _memory_store is None:
        _memory_store = MemoryStore()
    return _memory_store
