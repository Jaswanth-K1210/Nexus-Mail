"""
Nexus Mail — AI Provider Abstraction
Unified interface for Groq and OpenAI. Groq preferred for speed.
"""

import json
from groq import AsyncGroq
from openai import AsyncOpenAI
from app.core.config import get_settings

import structlog

logger = structlog.get_logger(__name__)


class AIProvider:
    """Abstract AI provider that routes to Groq or OpenAI."""

    def __init__(self):
        self.settings = get_settings()
        self._groq_client: AsyncGroq | None = None
        self._openai_client: AsyncOpenAI | None = None

    @property
    def groq(self) -> AsyncGroq:
        if not self._groq_client:
            self._groq_client = AsyncGroq(api_key=self.settings.groq_api_key)
        return self._groq_client

    @property
    def openai(self) -> AsyncOpenAI:
        if not self._openai_client:
            base_url = "https://openrouter.ai/api/v1" if self.settings.openrouter_api_key.startswith("sk-or-") else None
            self._openai_client = AsyncOpenAI(
                api_key=self.settings.openrouter_api_key, 
                base_url=base_url
            )
        return self._openai_client

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> str:
        """
        Send a completion request to the configured AI provider.
        Returns the raw text response.
        """
        provider = self.settings.ai_provider
        model = self.settings.ai_model

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            if provider == "groq":
                kwargs = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}

                response = await self.groq.chat.completions.create(**kwargs)
                return response.choices[0].message.content

            elif provider == "openai":
                kwargs = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}

                response = await self.openai.chat.completions.create(**kwargs)
                return response.choices[0].message.content

            else:
                raise ValueError(f"Unknown AI provider: {provider}")

        except Exception as e:
            logger.error("AI completion failed", provider=provider, error=str(e))
            raise

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 2048,
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
        )

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from the response
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
        )

        result = {}
        for line in response.split("\n"):
            if ":" in line:
                key, val = line.split(":", 1)
                result[key.strip().lower()] = val.strip()
        return result

    async def complete_json_validated(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        max_retries: int = 2,
    ) -> dict:
        """
        Send a completion request, parse as JSON, and validate against a Pydantic model.

        ARCHITECTURE FIX (Inbox Zero Analysis):
        - Inbox Zero uses Zod schemas to validate every LLM response
        - If validation fails, a retry loop with corrective prompting kicks in
        - The backend NEVER executes an action based on invalid/hallucinated output

        Args:
            response_model: A Pydantic BaseModel class to validate against
            max_retries: Number of retry attempts with corrective prompting

        Returns:
            Validated dict matching the Pydantic schema
        """
        from pydantic import ValidationError

        last_error = None

        for attempt in range(1 + max_retries):
            try:
                # On retry, inject the validation error into the prompt
                effective_prompt = user_prompt
                if attempt > 0 and last_error:
                    effective_prompt = (
                        f"{user_prompt}\n\n"
                        f"IMPORTANT: Your previous response failed validation with this error:\n"
                        f"{last_error}\n"
                        f"Please fix your response to match the required schema exactly."
                    )

                raw_result = await self.complete_json(
                    system_prompt=system_prompt,
                    user_prompt=effective_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                # Validate against the Pydantic model
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
