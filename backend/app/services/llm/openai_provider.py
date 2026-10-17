"""OpenAI LLM Provider implementation using OpenAI Async Client."""
import asyncio
import json
import logging
import time
from typing import Optional, TypeVar
import openai
from pydantic import BaseModel, ValidationError
from app.core.config import settings
from app.services.llm.base import (
    LLMAuthError,
    LLMError,
    LLMProvider,
    LLMRateLimitError,
    LLMResponse,
    LLMTimeoutError,
    LLMUsage,
    LLMValidationError,
)
from app.services.llm.safety import SYSTEM_SECURITY_POLICY

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class OpenAIProvider(LLMProvider):
    """OpenAI model provider with JSON mode and Pydantic validation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: float = 60.0,
        client: Optional[openai.AsyncOpenAI] = None,
        provider_name: str = "openai",
    ):
        key = api_key or settings.openai_api_key.get_secret_value()
        if not key:
            raise LLMAuthError(f"{provider_name.capitalize()} API key is not configured. Set DEVSQUAD_{provider_name.upper()}_API_KEY.")

        self._model = model or settings.openai_model
        self._provider_name = provider_name
        self.timeout = timeout_seconds
        resolved_base_url = base_url or settings.openai_base_url
        self.client = client or openai.AsyncOpenAI(
            api_key=key,
            base_url=resolved_base_url,
            timeout=self.timeout,
        )

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_name(self) -> str:
        return self._model

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[T],
        temperature: float = 0.0,
    ) -> LLMResponse[T]:
        """Call OpenAI to generate structured output conforming to response_schema."""
        full_system_prompt = (
            f"{SYSTEM_SECURITY_POLICY}\n\n"
            f"{system_prompt}\n\n"
            f"You must format your entire response as a valid JSON object strictly matching this schema:\n"
            f"{json.dumps(response_schema.model_json_schema())}"
        )
        start_time = time.perf_counter()

        messages = [
            {"role": "system", "content": full_system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        max_attempts = 3
        last_error = None

        for attempt in range(max_attempts):
            try:
                resp = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=self._model,
                        messages=messages,
                        temperature=temperature,
                        response_format={"type": "json_object"},
                    ),
                    timeout=self.timeout,
                )
                break
            except asyncio.TimeoutError as exc:
                raise LLMTimeoutError(f"OpenAI API timed out after {self.timeout}s.") from exc
            except openai.AuthenticationError as exc:
                raise LLMAuthError(f"OpenAI authentication failed: {str(exc)}") from exc
            except openai.RateLimitError as exc:
                if attempt < max_attempts - 1:
                    await asyncio.sleep(0.5 * (2 ** attempt))
                    last_error = exc
                    continue
                raise LLMRateLimitError(f"OpenAI rate limit exceeded: {str(exc)}") from exc
            except openai.APITimeoutError as exc:
                raise LLMTimeoutError(f"OpenAI request timed out: {str(exc)}") from exc
            except openai.APIError as exc:
                raise LLMError(f"OpenAI API error: {str(exc)}") from exc
            except Exception as exc:
                raise LLMError(f"Unexpected error calling OpenAI API: {str(exc)}") from exc
        else:
            if last_error:
                raise LLMRateLimitError(f"OpenAI rate limit exceeded after retries: {str(last_error)}") from last_error
            raise LLMError("OpenAI call failed after retries.")

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        raw_text = resp.choices[0].message.content or ""

        # Validate with Pydantic V2
        try:
            parsed_data = response_schema.model_validate_json(raw_text)
        except (ValidationError, json.JSONDecodeError) as exc:
            raise LLMValidationError(
                f"Model response failed schema validation for {response_schema.__name__}: {str(exc)}",
                details={"raw_text": raw_text[:500]},
            ) from exc

        usage = LLMUsage(
            prompt_tokens=resp.usage.prompt_tokens if resp.usage else None,
            completion_tokens=resp.usage.completion_tokens if resp.usage else None,
            total_tokens=resp.usage.total_tokens if resp.usage else None,
            latency_ms=latency_ms,
        )

        return LLMResponse(
            data=parsed_data,
            raw_response=raw_text,
            model=self._model,
            provider="openai",
            usage=usage,
        )
