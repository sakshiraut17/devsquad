"""LLM Provider Factory selecting configured AI backend."""
from typing import Optional
from app.core.config import Settings, settings
from app.core.exceptions import ConfigurationError
from app.services.llm.base import LLMProvider
from app.services.llm.gemini_provider import GeminiProvider
from app.services.llm.openai_provider import OpenAIProvider


def get_llm_provider(cfg: Optional[Settings] = None) -> LLMProvider:
    """
    Factory function returning the configured LLMProvider.
    Raises ConfigurationError if the provider or its credentials are unconfigured.
    Never silently switches providers.
    """
    current_settings = cfg or settings
    provider_name = current_settings.llm_provider.lower()

    if provider_name == "gemini":
        key = current_settings.gemini_api_key.get_secret_value()
        if not key:
            raise ConfigurationError(
                "Gemini provider is selected but DEVSQUAD_GEMINI_API_KEY is not configured in .env."
            )
        return GeminiProvider(
            api_key=key,
            model=current_settings.gemini_model,
        )

    if provider_name == "openai":
        key = current_settings.openai_api_key.get_secret_value()
        if not key:
            raise ConfigurationError(
                "OpenAI provider is selected but DEVSQUAD_OPENAI_API_KEY is not configured in .env."
            )
        return OpenAIProvider(
            api_key=key,
            model=current_settings.openai_model,
            base_url=current_settings.openai_base_url,
            provider_name="openai",
        )

    if provider_name == "groq":
        key = current_settings.groq_api_key.get_secret_value()
        if not key:
            raise ConfigurationError(
                "Groq provider is selected but DEVSQUAD_GROQ_API_KEY is not configured in .env."
            )
        return OpenAIProvider(
            api_key=key,
            model=current_settings.groq_model,
            base_url=current_settings.groq_base_url,
            provider_name="groq",
        )

    raise ConfigurationError(
        f"Unsupported LLM provider '{provider_name}'. Must be 'gemini', 'openai', or 'groq'."
    )
