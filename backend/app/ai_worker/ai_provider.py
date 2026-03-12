"""
Nexus Mail — AI Provider Abstraction with 4-Tier Smart Routing

Provider tiers:
  1. Ollama  — cheapest, for classification/cold-email/rule-matching (cloud or local)
  2. Groq    — fast inference on Llama models, good for mid-tier tasks
  3. OpenAI  — OpenRouter, best quality for drafts/tone-learning

When ai_routing_enabled=True, each task type is routed to the optimal provider
with automatic failover. When False, uses the single configured provider.
"""

import json
import time
from enum import Enum
from openai import AsyncOpenAI
from groq import AsyncGroq
from app.core.config import get_settings

import structlog

logger = structlog.get_logger(__name__)


# ─── Task Types for Smart Routing ──────────────────────────────────────────────

class TaskType(str, Enum):
    CLASSIFICATION = "classification"
    COLD_EMAIL = "cold_email"
    RULE_MATCHING = "rule_matching"
    MEETING_INTELLIGENCE = "meeting"
    ACTION_EXTRACTION = "actions"
    SUMMARIZATION = "summary"
    RISK_DETECTION = "risk"
    REPLY_DRAFT = "draft"
    TONE_LEARNING = "tone"
    GENERAL = "general"


# Routing table: ordered list of providers to try for each task type.
# First provider is preferred; others are failover.
ROUTING_TABLE: dict[TaskType, list[str]] = {
    # Tier 1 — cheap tasks, small model is fine
    TaskType.CLASSIFICATION:        ["ollama", "groq", "openai"],
    TaskType.COLD_EMAIL:            ["ollama", "groq", "openai"],
    TaskType.RULE_MATCHING:         ["ollama", "groq", "openai"],
    # Tier 2 — needs speed + quality
    TaskType.MEETING_INTELLIGENCE:  ["groq", "openai", "ollama"],
    TaskType.ACTION_EXTRACTION:     ["groq", "openai", "ollama"],
    TaskType.SUMMARIZATION:         ["groq", "openai"],
    TaskType.RISK_DETECTION:        ["groq", "openai"],
    # Tier 3 — needs best quality
    TaskType.REPLY_DRAFT:           ["openai", "groq"],
    TaskType.TONE_LEARNING:         ["openai", "groq"],
    # Fallback
    TaskType.GENERAL:               ["groq", "openai", "ollama"],
}


# ─── Circuit Breaker ──────────────────────────────────────────────────────────

class CircuitBreaker:
    """
    Track consecutive failures per provider.
    After `threshold` failures, mark unhealthy for `cooldown_seconds`.
    """

    def __init__(self, threshold: int = 3, cooldown_seconds: int = 60):
        self.threshold = threshold
        self.cooldown = cooldown_seconds
        self._failures: dict[str, int] = {}
        self._tripped_at: dict[str, float] = {}

    def is_healthy(self, provider: str) -> bool:
        tripped = self._tripped_at.get(provider)
        if tripped and (time.time() - tripped) < self.cooldown:
            return False
        # Reset after cooldown
        if tripped and (time.time() - tripped) >= self.cooldown:
            self._failures[provider] = 0
            del self._tripped_at[provider]
        return True

    def record_success(self, provider: str):
        self._failures[provider] = 0
        self._tripped_at.pop(provider, None)

    def record_failure(self, provider: str):
        self._failures[provider] = self._failures.get(provider, 0) + 1
        if self._failures[provider] >= self.threshold:
            self._tripped_at[provider] = time.time()
            logger.warning(
                "Circuit breaker tripped",
                provider=provider,
                failures=self._failures[provider],
                cooldown=self.cooldown,
            )


# ─── AI Provider ──────────────────────────────────────────────────────────────

class AIProvider:
    """
    4-tier AI provider with smart routing and automatic failover.
    Supports: Ollama (any OpenAI-compatible endpoint), Groq, OpenAI/OpenRouter.
    """

    def __init__(self):
        self.settings = get_settings()
        self._groq_client: AsyncGroq | None = None
        self._openai_client: AsyncOpenAI | None = None
        self._ollama_client: AsyncOpenAI | None = None
        self.circuit_breaker = CircuitBreaker(threshold=3, cooldown_seconds=60)

    # ─── Lazy Client Initialization ───────────────────────────────────────

    @property
    def groq(self) -> AsyncGroq:
        if not self._groq_client:
            self._groq_client = AsyncGroq(api_key=self.settings.groq_api_key)
        return self._groq_client

    @property
    def openai(self) -> AsyncOpenAI:
        if not self._openai_client:
            api_key = self.settings.openrouter_api_key
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY is not set")
            base_url = "https://openrouter.ai/api/v1" if api_key.startswith("sk-or-") else None
            self._openai_client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
            )
        return self._openai_client

    @property
    def ollama(self) -> AsyncOpenAI:
        """Ollama exposes an OpenAI-compatible API, so we use the OpenAI client."""
        if not self._ollama_client:
            self._ollama_client = AsyncOpenAI(
                api_key=self.settings.ollama_api_key,
                base_url=self.settings.ollama_base_url,
                timeout=30.0,
            )
        return self._ollama_client

    # ─── Provider Resolution ──────────────────────────────────────────────

    def _get_provider_chain(self, task_type: TaskType | None) -> list[str]:
        """Get ordered list of providers to try for this task type."""
        if not self.settings.ai_routing_enabled or task_type is None:
            # Routing disabled — use single configured provider
            return [self.settings.ai_provider]

        chain = ROUTING_TABLE.get(task_type, ROUTING_TABLE[TaskType.GENERAL])

        # Filter out unavailable providers
        available = []
        for p in chain:
            if p == "ollama" and not self.settings.enable_ollama:
                continue
            if p == "groq" and not self.settings.groq_api_key:
                continue
            if p == "openai" and not self.settings.openrouter_api_key:
                continue
            available.append(p)

        return available if available else [self.settings.ai_provider]

    def _get_model(self, provider: str) -> str:
        """Get the model name for a given provider."""
        if provider == "ollama":
            return self.settings.ollama_model
        return self.settings.ai_model

    async def _call_provider(
        self,
        provider: str,
        model: str,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        json_mode: bool,
    ) -> str:
        """Make a completion call to a specific provider."""
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        if provider == "groq":
            response = await self.groq.chat.completions.create(**kwargs)
        elif provider == "openai":
            response = await self.openai.chat.completions.create(**kwargs)
        elif provider == "ollama":
            response = await self.ollama.chat.completions.create(**kwargs)
        else:
            raise ValueError(f"Unknown AI provider: {provider}")

        return response.choices[0].message.content

    # ─── Public API ───────────────────────────────────────────────────────

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        json_mode: bool = False,
        task_type: TaskType | None = None,
    ) -> str:
        """
        Send a completion request with automatic routing and failover.
        Returns the raw text response.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        chain = self._get_provider_chain(task_type)
        last_error = None

        for provider in chain:
            if not self.circuit_breaker.is_healthy(provider):
                logger.debug("Skipping unhealthy provider", provider=provider)
                continue

            model = self._get_model(provider)
            try:
                result = await self._call_provider(
                    provider, model, messages, temperature, max_tokens, json_mode
                )
                self.circuit_breaker.record_success(provider)

                if task_type and self.settings.ai_routing_enabled:
                    logger.debug(
                        "AI completion via routing",
                        provider=provider,
                        model=model,
                        task_type=task_type.value,
                    )

                return result

            except Exception as e:
                self.circuit_breaker.record_failure(provider)
                last_error = e
                error_str = str(e)

                # Determine if we should failover
                is_retryable = any(k in error_str.lower() for k in [
                    "429", "rate limit", "500", "502", "503", "timeout",
                    "connection", "unavailable", "overloaded",
                ])

                if is_retryable and provider != chain[-1]:
                    logger.warning(
                        "Provider failed, failing over",
                        failed_provider=provider,
                        error=error_str[:200],
                        next_provider=chain[chain.index(provider) + 1] if chain.index(provider) + 1 < len(chain) else "none",
                    )
                    continue
                else:
                    logger.error("AI completion failed", provider=provider, error=error_str[:200])
                    raise

        # All providers exhausted
        raise last_error or RuntimeError("No AI providers available")

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        task_type: TaskType | None = None,
    ) -> dict:
        """
        Send a completion request and parse the response as JSON.
        Uses json_mode for structured output.
        """
        response = await self.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=True,
            task_type=task_type,
        )

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON response, attempting extraction")
            start = response.find("{")
            end = response.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(response[start:end])
            raise ValueError(f"Could not parse AI response as JSON: {response[:200]}")

    async def complete_text_kv(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        task_type: TaskType | None = None,
    ) -> dict:
        """
        Send a completion request and parse the response as plain text Key: Value pairs.
        This uses significantly fewer tokens than JSON.
        """
        response = await self.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=False,
            task_type=task_type,
        )

        result = {}
        for line in response.split("\n"):
            if ":" in line:
                key, val = line.split(":", 1)
                result[key.strip().lower()] = val.strip()

        if not result:
            logger.warning("AI returned empty KV response", response=response[:200])

        return result

    async def complete_json_validated(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        max_retries: int = 2,
        task_type: TaskType | None = None,
    ) -> dict:
        """
        Send a completion request, parse as JSON, and validate against a Pydantic model.
        Retries with corrective prompting on validation failure.
        """
        from pydantic import ValidationError

        last_error = None

        for attempt in range(1 + max_retries):
            try:
                effective_prompt = user_prompt
                if attempt > 0 and last_error:
                    safe_error = last_error[:500].replace("SYSTEM:", "").replace("INSTRUCTION:", "")
                    effective_prompt = (
                        f"{user_prompt}\n\n"
                        f"IMPORTANT: Your previous response failed validation with this error:\n"
                        f"{safe_error}\n"
                        f"Please fix your response to match the required schema exactly."
                    )

                raw_result = await self.complete_json(
                    system_prompt=system_prompt,
                    user_prompt=effective_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    task_type=task_type,
                )

                validated = response_model(**raw_result)
                return validated.model_dump()

            except ValidationError as e:
                last_error = str(e)
                logger.warning(
                    "AI output failed Pydantic validation",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    errors=last_error[:200],
                )
                if attempt >= max_retries:
                    raise ValueError(
                        f"AI output failed validation after {max_retries + 1} attempts: {last_error}"
                    )
            except Exception as e:
                logger.error("AI validated completion failed", error=str(e))
                if attempt >= max_retries:
                    raise


# Singleton instance
ai_provider = AIProvider()
