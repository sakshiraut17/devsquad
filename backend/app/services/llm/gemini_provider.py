"""Gemini LLM Provider implementation using Google GenAI SDK."""
import asyncio
import json
import logging
import time
from typing import Optional, TypeVar
from google import genai
from google.genai import types
from google.genai.errors import APIError
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


class GeminiProvider(LLMProvider):
    """Google Gemini model provider with structured JSON output and schema validation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: float = 60.0,
        client: Optional[genai.Client] = None,
    ):
        key = api_key or settings.gemini_api_key.get_secret_value()
        if not key:
            raise LLMAuthError("Gemini API key is not configured. Set DEVSQUAD_GEMINI_API_KEY.")

        self._model = model or settings.gemini_model
        self.timeout = timeout_seconds
        self.client = client or genai.Client(api_key=key)

    @property
    def provider_name(self) -> str:
        return "gemini"

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
        """Call Gemini to generate schema-validated structured response."""
        full_system_prompt = f"{SYSTEM_SECURITY_POLICY}\n\n{system_prompt}"
        start_time = time.perf_counter()

        config = types.GenerateContentConfig(
            system_instruction=full_system_prompt,
            response_mime_type="application/json",
            response_schema=response_schema,
            temperature=temperature,
        )

        max_attempts = 3
        last_error = None

        for attempt in range(max_attempts):
            try:
                resp = await asyncio.wait_for(
                    self.client.aio.models.generate_content(
                        model=self._model,
                        contents=user_prompt,
                        config=config,
                    ),
                    timeout=self.timeout,
                )
                break
            except asyncio.TimeoutError as exc:
                raise LLMTimeoutError(f"Gemini API timed out after {self.timeout}s.") from exc
            except APIError as exc:
                error_msg = str(exc)
                if exc.code == 401 or "API_KEY_INVALID" in error_msg:
                    raise LLMAuthError(f"Gemini authentication failed: {error_msg}") from exc
                if (exc.code == 429 or "RESOURCE_EXHAUSTED" in error_msg) and attempt < max_attempts - 1:
                    await asyncio.sleep(0.5 * (2 ** attempt))
                    last_error = exc
                    continue
                if exc.code == 429 or "RESOURCE_EXHAUSTED" in error_msg:
                    raise LLMRateLimitError(f"Gemini rate limit exceeded: {error_msg}") from exc
                raise LLMError(f"Gemini API error (code {exc.code}): {error_msg}") from exc
            except Exception as exc:
                raise LLMError(f"Unexpected error calling Gemini API: {str(exc)}") from exc
        else:
            if last_error:
                raise LLMRateLimitError(f"Gemini rate limit exceeded after retries: {str(last_error)}") from last_error
            raise LLMError("Gemini call failed after retries.")

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        raw_text = resp.text or ""

        # Validate with Pydantic V2
        try:
            parsed_data = response_schema.model_validate_json(raw_text)
        except (ValidationError, json.JSONDecodeError) as exc:
            raise LLMValidationError(
                f"Model response failed schema validation for {response_schema.__name__}: {str(exc)}",
                details={"raw_text": raw_text[:500]},
            ) from exc

        # Extract usage telemetry if available
        prompt_tokens = getattr(resp.usage_metadata, "prompt_token_count", None) if hasattr(resp, "usage_metadata") else None
        completion_tokens = getattr(resp.usage_metadata, "candidates_token_count", None) if hasattr(resp, "usage_metadata") else None
        total_tokens = getattr(resp.usage_metadata, "total_token_count", None) if hasattr(resp, "usage_metadata") else None

        usage = LLMUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
        )

        return LLMResponse(
            data=parsed_data,
            raw_response=raw_text,
            model=self._model,
            provider="gemini",
            usage=usage,
        )
