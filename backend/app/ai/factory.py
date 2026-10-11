"""Choose the AI provider from settings: AI_PROVIDER, AI_MODEL, AI_API_KEY.

Model names live only in .env, never in code.
"""

from functools import lru_cache

from fastapi import Depends

from app.ai.base import AIProvider
from app.config import Settings, get_settings
from app.errors import AppError, ErrorCode

SUPPORTED_PROVIDERS = ("gemini",)


def get_ai_provider(settings: Settings = Depends(get_settings)) -> AIProvider:
    """FastAPI dependency; tests override it with a fake provider."""
    return _build_provider(
        settings.ai_provider.strip().lower(),
        settings.ai_model.strip(),
        settings.ai_api_key.strip(),
        settings.ai_timeout_seconds,
    )


@lru_cache(maxsize=4)  # one client per configuration, not per request
def _build_provider(name: str, model: str, api_key: str, timeout_seconds: float) -> AIProvider:
    if name not in SUPPORTED_PROVIDERS:
        raise AppError(
            ErrorCode.AI_ERROR,
            f"Unknown AI_PROVIDER '{name}', expected one of: {', '.join(SUPPORTED_PROVIDERS)}",
            500,
        )
    if not api_key:
        raise AppError(ErrorCode.AI_ERROR, "AI_API_KEY is not set in backend/.env", 500)
    if not model:
        raise AppError(ErrorCode.AI_ERROR, "AI_MODEL is not set in backend/.env", 500)

    # Imported here so the SDK only loads for the provider actually in use.
    from app.ai.gemini import GeminiProvider

    return GeminiProvider(api_key=api_key, model=model, timeout_seconds=timeout_seconds)
