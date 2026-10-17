"""Optional live integration tests for GitHub and LLM providers.

These tests are skipped by default during standard CI / local test runs unless
DEVSQUAD_RUN_LIVE_TESTS is explicitly set to "1" or "true" and valid credentials exist.
"""

import os
import pytest
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.services.github_service import GitHubService
from app.services.llm.gemini_provider import GeminiProvider
from app.services.llm.openai_provider import OpenAIProvider


class LiveSummarySchema(BaseModel):
    summary: str = Field(description="One-sentence summary")
    status: str = Field(description="Status string: OK")


RUN_LIVE = os.getenv("DEVSQUAD_RUN_LIVE_TESTS", "").lower() in ("1", "true", "yes")


@pytest.mark.skipif(not RUN_LIVE, reason="Live integration tests disabled. Set DEVSQUAD_RUN_LIVE_TESTS=1 to run.")
class TestLiveIntegrations:
    __test__ = True

    @pytest.mark.asyncio
    async def test_live_github_public_repo(self):
        settings = get_settings()
        raw_token = settings.github_token.get_secret_value() if settings.github_token else None
        service = GitHubService(token=raw_token or None)
        repo = await service.get_repository("octocat", "Hello-World")
        assert repo.name == "Hello-World"
        assert repo.owner == "octocat"
        assert not repo.is_private

    @pytest.mark.asyncio
    async def test_live_gemini_provider(self):
        settings = get_settings()
        gemini_key = settings.gemini_api_key.get_secret_value()
        if not gemini_key:
            pytest.skip("DEVSQUAD_GEMINI_API_KEY not set")
        provider = GeminiProvider(api_key=gemini_key, model=settings.gemini_model)
        res = await provider.generate_structured(
            system_prompt="Respond strictly with the requested JSON schema.",
            user_prompt="Say Hello DevSquad and set status to OK.",
            response_schema=LiveSummarySchema,
        )
        assert res.data.status == "OK"
        assert len(res.data.summary) > 0

    @pytest.mark.asyncio
    async def test_live_openai_provider(self):
        settings = get_settings()
        openai_key = settings.openai_api_key.get_secret_value()
        if not openai_key:
            pytest.skip("DEVSQUAD_OPENAI_API_KEY not set")
        provider = OpenAIProvider(api_key=openai_key, model=settings.openai_model)
        res = await provider.generate_structured(
            system_prompt="Respond strictly with the requested JSON schema.",
            user_prompt="Say Hello DevSquad and set status to OK.",
            response_schema=LiveSummarySchema,
        )
        assert res.data.status == "OK"
        assert len(res.data.summary) > 0

