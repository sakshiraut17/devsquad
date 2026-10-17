"""LLM Provider abstraction interface and common response schemas."""
from abc import ABC, abstractmethod
from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field
from app.core.exceptions import DevSquadException

T = TypeVar("T", bound=BaseModel)


class LLMError(DevSquadException):
    """Base error for LLM provider operations."""


class LLMAuthError(LLMError):
    """Raised when provider authentication fails (e.g. invalid API key)."""


class LLMRateLimitError(LLMError):
    """Raised when provider rate limits or quotas are exceeded."""


class LLMTimeoutError(LLMError):
    """Raised when an inference call times out."""


class LLMValidationError(LLMError):
    """Raised when the model output fails schema validation."""


class LLMUsage(BaseModel):
    """Token and latency telemetry captured from a model call."""
    model_config = ConfigDict(extra="ignore")

    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    latency_ms: float = 0.0


class LLMResponse(BaseModel, Generic[T]):
    """Structured response container wrapping parsed payload and telemetry."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    data: T
    raw_response: str
    model: str
    provider: str
    usage: LLMUsage


class LLMProvider(ABC):
    """Abstract interface for all AI model providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g. 'gemini', 'openai')."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Target model identifier."""

    @abstractmethod
    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[T],
        temperature: float = 0.0,
    ) -> LLMResponse[T]:
        """
        Generate structured output conforming to the given Pydantic schema.
        Accepts system instructions and untrusted user context separately.
        """
