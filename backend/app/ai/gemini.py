"""Google Gemini provider (google-genai SDK)."""

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.ai.base import AIProvider
from app.errors import AppError, ErrorCode

# Overload and server errors are usually gone within seconds, so the SDK retries them with
# exponential backoff. 429 is not retried: quota errors don't clear in seconds.
_RETRYABLE_STATUS_CODES = [500, 502, 503, 504]


class GeminiProvider(AIProvider):
    def __init__(
        self, api_key: str, model: str, timeout_seconds: float, max_attempts: int = 2
    ) -> None:
        self._model = model
        retry = types.HttpRetryOptions(
            attempts=max(1, max_attempts),
            initial_delay=2.0,
            max_delay=8.0,
            http_status_codes=_RETRYABLE_STATUS_CODES,
        )
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=int(timeout_seconds * 1000), retry_options=retry
            ),
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
        except genai_errors.APIError as exc:
            raise AppError(ErrorCode.AI_ERROR, describe_api_error(exc, self._model), 502) from exc
        except Exception as exc:  # network failures and timeouts
            raise AppError(
                ErrorCode.AI_ERROR,
                f"Could not reach the AI service ({type(exc).__name__}). "
                "Check your internet connection and try again.",
                502,
            ) from exc

        if not response.text:
            raise AppError(ErrorCode.AI_ERROR, "AI returned an empty answer", 502)
        return response.text


def describe_api_error(exc: genai_errors.APIError, model: str) -> str:
    """Turn Gemini's error into something a user can act on."""
    status = (exc.status or "").upper()
    message = exc.message or ""

    if exc.code == 503 or status == "UNAVAILABLE":
        return (
            "The AI model is overloaded right now. Try again in a minute, "
            "or set a less busy AI_MODEL in backend/.env."
        )
    if exc.code == 429 or status == "RESOURCE_EXHAUSTED":
        return (
            "The AI rate limit or quota was reached. Wait a minute, "
            "or check your limits in Google AI Studio."
        )
    if exc.code in (401, 403) or "api key" in message.lower():
        return "Gemini rejected the API key. Check AI_API_KEY in backend/.env."
    if exc.code == 404 or status == "NOT_FOUND":
        return f"The model '{model}' was not found. Check AI_MODEL in backend/.env."
    return f"Gemini returned an error ({exc.code} {exc.status}): {message}"
