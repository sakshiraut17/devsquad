"""Unit tests for Gemini, OpenAI, and LLM Provider abstraction."""
import asyncio
from unittest.mock import AsyncMock, MagicMock
import openai
import pytest
from google.genai.errors import APIError
from pydantic import BaseModel
from app.core.config import Settings
from app.core.exceptions import ConfigurationError
from app.services.llm import (
    GeminiProvider,
    LLMAuthError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMValidationError,
    OpenAIProvider,
    get_llm_provider,
)


class MockPlanSchema(BaseModel):
    objective: str
    steps_count: int


# --- Gemini Provider Tests ---

@pytest.mark.asyncio
async def test_gemini_provider_generate_structured_success():
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = '{"objective": "Fix Bug", "steps_count": 3}'
    mock_resp.usage_metadata.prompt_token_count = 100
    mock_resp.usage_metadata.candidates_token_count = 50
    mock_resp.usage_metadata.total_token_count = 150

    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_resp)

    provider = GeminiProvider(api_key="fake-key", client=mock_client)
    res = await provider.generate_structured(
        system_prompt="System instructions",
        user_prompt="Task prompt",
        response_schema=MockPlanSchema,
    )

    assert res.data.objective == "Fix Bug"
    assert res.data.steps_count == 3
    assert res.provider == "gemini"
    assert res.usage.total_tokens == 150
    assert res.usage.latency_ms > 0


@pytest.mark.asyncio
async def test_gemini_provider_schema_validation_failure():
    mock_client = MagicMock()
    mock_resp = MagicMock()
    # Missing required field 'steps_count' or invalid type
    mock_resp.text = '{"objective": "Fix Bug", "steps_count": "invalid_integer"}'
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_resp)

    provider = GeminiProvider(api_key="fake-key", client=mock_client)
    with pytest.raises(LLMValidationError):
        await provider.generate_structured(
            system_prompt="Sys",
            user_prompt="User",
            response_schema=MockPlanSchema,
        )


@pytest.mark.asyncio
async def test_gemini_provider_rate_limit_and_timeout(monkeypatch):
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    mock_client = MagicMock()
    api_err = APIError(429, {"error": {"message": "Resource has been exhausted"}})
    mock_client.aio.models.generate_content = AsyncMock(side_effect=api_err)

    provider = GeminiProvider(api_key="fake-key", client=mock_client)
    with pytest.raises(LLMRateLimitError):
        await provider.generate_structured("Sys", "User", MockPlanSchema)
    assert mock_client.aio.models.generate_content.call_count == 3

    # Test timeout
    mock_client.aio.models.generate_content = AsyncMock(side_effect=asyncio.TimeoutError())
    provider_timeout = GeminiProvider(api_key="fake-key", client=mock_client, timeout_seconds=0.01)
    with pytest.raises(LLMTimeoutError):
        await provider_timeout.generate_structured("Sys", "User", MockPlanSchema)


@pytest.mark.asyncio
async def test_gemini_provider_retry_success(monkeypatch):
    sleep_mock = AsyncMock()
    monkeypatch.setattr(asyncio, "sleep", sleep_mock)

    mock_client = MagicMock()
    api_err = APIError(429, {"error": {"message": "Resource has been exhausted"}})
    mock_resp = MagicMock()
    mock_resp.text = '{"objective": "Retry Succeeded", "steps_count": 3}'
    mock_resp.usage_metadata.prompt_token_count = 10
    mock_resp.usage_metadata.candidates_token_count = 5
    mock_resp.usage_metadata.total_token_count = 15

    mock_client.aio.models.generate_content = AsyncMock(
        side_effect=[api_err, mock_resp]
    )

    provider = GeminiProvider(api_key="fake-key", client=mock_client)
    res = await provider.generate_structured("Sys", "User", MockPlanSchema)

    assert mock_client.aio.models.generate_content.call_count == 2
    assert res.data.objective == "Retry Succeeded"
    assert sleep_mock.call_count == 1


def test_gemini_provider_requires_api_key():
    with pytest.raises(LLMAuthError):
        GeminiProvider(api_key="")


# --- OpenAI Provider Tests ---

@pytest.mark.asyncio
async def test_openai_provider_generate_structured_success():
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = '{"objective": "Refactor Code", "steps_count": 5}'

    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]
    mock_resp.usage.prompt_tokens = 80
    mock_resp.usage.completion_tokens = 40
    mock_resp.usage.total_tokens = 120

    mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)

    provider = OpenAIProvider(api_key="fake-key", client=mock_client)
    res = await provider.generate_structured(
        system_prompt="System instructions",
        user_prompt="Task prompt",
        response_schema=MockPlanSchema,
    )

    assert res.data.objective == "Refactor Code"
    assert res.data.steps_count == 5
    assert res.provider == "openai"
    assert res.usage.total_tokens == 120


@pytest.mark.asyncio
async def test_openai_provider_auth_and_rate_limit_errors(monkeypatch):
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    mock_client = MagicMock()
    # Auth error
    mock_client.chat.completions.create = AsyncMock(
        side_effect=openai.AuthenticationError("Invalid API key", response=MagicMock(), body=None)
    )
    provider = OpenAIProvider(api_key="fake-key", client=mock_client)
    with pytest.raises(LLMAuthError):
        await provider.generate_structured("Sys", "User", MockPlanSchema)

    # Rate limit error
    mock_client.chat.completions.create = AsyncMock(
        side_effect=openai.RateLimitError("Quota exceeded", response=MagicMock(), body=None)
    )
    with pytest.raises(LLMRateLimitError):
        await provider.generate_structured("Sys", "User", MockPlanSchema)
    assert mock_client.chat.completions.create.call_count == 3


@pytest.mark.asyncio
async def test_openai_provider_retry_success(monkeypatch):
    sleep_mock = AsyncMock()
    monkeypatch.setattr(asyncio, "sleep", sleep_mock)

    mock_client = MagicMock()
    rate_err = openai.RateLimitError("Quota exceeded", response=MagicMock(), body=None)

    mock_choice = MagicMock()
    mock_choice.message.content = '{"objective": "OpenAI Retry Succeeded", "steps_count": 2}'
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]
    mock_resp.usage.prompt_tokens = 50
    mock_resp.usage.completion_tokens = 25
    mock_resp.usage.total_tokens = 75

    mock_client.chat.completions.create = AsyncMock(
        side_effect=[rate_err, mock_resp]
    )

    provider = OpenAIProvider(api_key="fake-key", client=mock_client)
    res = await provider.generate_structured("Sys", "User", MockPlanSchema)

    assert mock_client.chat.completions.create.call_count == 2
    assert res.data.objective == "OpenAI Retry Succeeded"
    assert sleep_mock.call_count == 1



# --- Provider Factory Tests ---

def test_get_llm_provider_selection_and_errors():
    # 1. Unconfigured Gemini raises ConfigurationError
    cfg_gemini = Settings(llm_provider="gemini", gemini_api_key="")
    with pytest.raises(ConfigurationError) as exc1:
        get_llm_provider(cfg_gemini)
    assert "DEVSQUAD_GEMINI_API_KEY" in str(exc1.value)

    # 2. Configured Gemini succeeds
    cfg_gemini_ok = Settings(llm_provider="gemini", gemini_api_key="test-gemini-key")
    p_gemini = get_llm_provider(cfg_gemini_ok)
    assert isinstance(p_gemini, GeminiProvider)

    # 3. Configured OpenAI succeeds
    cfg_openai_ok = Settings(llm_provider="openai", openai_api_key="test-openai-key")
    p_openai = get_llm_provider(cfg_openai_ok)
    assert isinstance(p_openai, OpenAIProvider)

    # 4. Unsupported provider raises ConfigurationError
    cfg_bad = Settings()
    cfg_bad.llm_provider = "unsupported_provider"  # type: ignore
    with pytest.raises(ConfigurationError):
        get_llm_provider(cfg_bad)
