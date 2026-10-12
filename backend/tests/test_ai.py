from types import SimpleNamespace

import pytest
from google.genai import errors as genai_errors

from app.ai.base import AIProvider, extract_sql
from app.ai.factory import _build_provider
from app.ai.gemini import GeminiProvider
from app.ai.prompts import SYSTEM_PROMPT, build_user_prompt
from app.errors import AppError, ErrorCode
from app.services.schema_service import SchemaColumn, SchemaTable

SALES = SchemaTable(
    name="sales",
    row_count=2,
    columns=[
        SchemaColumn(name="city", original_name="City", type="TEXT"),
        SchemaColumn(name="amount", original_name="amount", type="INTEGER"),
    ],
    sample_rows=[["Praha", 100], ["x" * 500, 250]],
)


# --- answer cleanup ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        "SELECT 1",
        "  SELECT 1\n",
        "```sql\nSELECT 1\n```",
        "```\nSELECT 1\n```",
        "Here you go:\n```sql\nSELECT 1\n```\nHope this helps",
        "```sql\nSELECT 1",  # fence never closed
    ],
)
def test_extract_sql_strips_markdown(raw: str) -> None:
    assert extract_sql(raw) == "SELECT 1"


def test_cannot_answer_becomes_readable_error() -> None:
    with pytest.raises(AppError) as exc_info:
        extract_sql("CANNOT_ANSWER: the data has no weather information")
    assert exc_info.value.code == ErrorCode.AI_ERROR
    assert exc_info.value.status_code == 422
    assert exc_info.value.message == "the data has no weather information"


@pytest.mark.parametrize("raw", ["", "   ", "```sql\n```"])
def test_empty_answer_is_an_error(raw: str) -> None:
    with pytest.raises(AppError) as exc_info:
        extract_sql(raw)
    assert exc_info.value.code == ErrorCode.AI_ERROR


# --- prompt -----------------------------------------------------------------------------


def test_prompt_contains_schema_original_names_samples_and_question() -> None:
    prompt = build_user_prompt([SALES], "Top cities by amount")
    assert 'Table "sales" (2 rows)' in prompt
    assert '"city" TEXT  (original name: "City")' in prompt
    assert '"amount" INTEGER\n' in prompt  # no redundant original name
    assert '["Praha", 100]' in prompt
    assert prompt.endswith("Question: Top cities by amount")


def test_prompt_truncates_long_sample_values() -> None:
    prompt = build_user_prompt([SALES], "q")
    assert "x" * 81 not in prompt
    assert "x" * 80 + "…" in prompt


def test_generate_sql_sends_system_and_user_prompt_and_cleans_answer() -> None:
    class Recorder(AIProvider):
        def complete(self, system_prompt: str, user_prompt: str) -> str:
            self.calls = (system_prompt, user_prompt)
            return "```sql\nSELECT * FROM sales\n```"

    provider = Recorder()
    assert provider.generate_sql([SALES], "everything") == "SELECT * FROM sales"
    assert provider.calls[0] == SYSTEM_PROMPT
    assert "Question: everything" in provider.calls[1]


# --- provider selection -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "model", "key", "expected"),
    [
        ("openai", "m", "k", "Unknown AI_PROVIDER"),
        ("gemini", "m", "", "AI_API_KEY"),
        ("gemini", "", "k", "AI_MODEL"),
    ],
)
def test_misconfiguration_is_a_clear_error(name: str, model: str, key: str, expected: str) -> None:
    with pytest.raises(AppError) as exc_info:
        _build_provider(name, model, key, 30)
    assert exc_info.value.code == ErrorCode.AI_ERROR
    assert expected in exc_info.value.message


def test_builds_gemini_provider() -> None:
    assert isinstance(_build_provider("gemini", "some-model", "key", 30), GeminiProvider)


# --- Gemini, with the SDK client replaced by a fake ----------------------------------------


def _gemini_with(generate_content) -> GeminiProvider:
    provider = GeminiProvider(api_key="test-key", model="some-model", timeout_seconds=30)
    provider._client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    return provider


def test_gemini_passes_model_prompts_and_zero_temperature() -> None:
    calls = {}

    def generate_content(*, model, contents, config):
        calls.update(model=model, contents=contents, config=config)
        return SimpleNamespace(text="SELECT 1")

    assert _gemini_with(generate_content).complete("system", "user") == "SELECT 1"
    assert calls["model"] == "some-model"
    assert calls["contents"] == "user"
    assert calls["config"].system_instruction == "system"
    assert calls["config"].temperature == 0


def test_gemini_network_failure_becomes_ai_error() -> None:
    def generate_content(**_):
        raise ConnectionError("network down")

    with pytest.raises(AppError) as exc_info:
        _gemini_with(generate_content).complete("s", "u")
    assert exc_info.value.code == ErrorCode.AI_ERROR
    assert exc_info.value.status_code == 502
    assert "Could not reach the AI service (ConnectionError)" in exc_info.value.message


def _api_error(code: int, status: str, message: str) -> genai_errors.APIError:
    return genai_errors.APIError(
        code, {"error": {"code": code, "status": status, "message": message}}
    )


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (_api_error(503, "UNAVAILABLE", "high demand"), "overloaded right now"),
        (_api_error(429, "RESOURCE_EXHAUSTED", "quota"), "rate limit or quota"),
        (
            _api_error(400, "INVALID_ARGUMENT", "API key not valid. Please pass a valid API key."),
            "rejected the API key",
        ),
        (_api_error(403, "PERMISSION_DENIED", "denied"), "rejected the API key"),
        (_api_error(404, "NOT_FOUND", "models/x is not found"), "'some-model' was not found"),
        (_api_error(500, "INTERNAL", "oops"), "Gemini returned an error (500 INTERNAL): oops"),
    ],
)
def test_gemini_api_errors_are_explained(error: genai_errors.APIError, expected: str) -> None:
    def generate_content(**_):
        raise error

    with pytest.raises(AppError) as exc_info:
        _gemini_with(generate_content).complete("s", "u")
    assert exc_info.value.code == ErrorCode.AI_ERROR
    assert expected in exc_info.value.message


def test_gemini_retries_transient_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}
    monkeypatch.setattr(
        "app.ai.gemini.genai.Client", lambda **kwargs: captured.update(kwargs) or object()
    )
    GeminiProvider(api_key="k", model="m", timeout_seconds=30)

    options = captured["http_options"]
    assert options.timeout == 30_000
    assert options.retry_options.attempts == 3
    assert 503 in options.retry_options.http_status_codes
    assert 429 not in options.retry_options.http_status_codes  # quota errors don't heal in seconds


def test_gemini_empty_response_becomes_ai_error() -> None:
    with pytest.raises(AppError) as exc_info:
        _gemini_with(lambda **_: SimpleNamespace(text=None)).complete("s", "u")
    assert exc_info.value.code == ErrorCode.AI_ERROR
