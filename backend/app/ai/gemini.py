"""Google Gemini provider (google-genai SDK)."""

from google import genai
from google.genai import types

from app.ai.base import AIProvider
from app.errors import AppError, ErrorCode


class GeminiProvider(AIProvider):
    def __init__(self, api_key: str, model: str, timeout_seconds: float) -> None:
        self._model = model
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=int(timeout_seconds * 1000)),
        )

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0,  # same question, same SQL
                ),
            )
        except Exception as exc:  # SDK, network and timeout errors alike
            raise AppError(ErrorCode.AI_ERROR, f"AI provider request failed: {exc}", 502) from exc

        if not response.text:
            raise AppError(ErrorCode.AI_ERROR, "AI returned an empty answer", 502)
        return response.text
