from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.ai.base import AIProvider
from app.ai.factory import get_ai_provider
from app.main import app


class FakeAI(AIProvider):
    """Returns a canned answer and records what it was asked."""

    def __init__(self) -> None:
        self.answer = "SELECT 1"
        self.prompts: list[str] = []

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.prompts.append(user_prompt)
        return self.answer


@pytest.fixture
def fake_ai(client: TestClient) -> Iterator[FakeAI]:
    fake = FakeAI()
    app.dependency_overrides[get_ai_provider] = lambda: fake
    yield fake


def workspace_with_sales(client: TestClient) -> str:
    workspace_id = client.post("/api/workspaces").json()["workspace_id"]
    csv = b"City,Amount ($)\nPrague,100\nBrno,250\nPrague,80\n"
    response = client.post(
        f"/api/workspaces/{workspace_id}/files", files=[("files", ("sales.csv", csv, "text/csv"))]
    )
    assert response.status_code == 200
    return workspace_id


def ask(client: TestClient, workspace_id: str, question: str):
    return client.post(f"/api/workspaces/{workspace_id}/query", json={"question": question})


def test_question_to_result(client: TestClient, fake_ai: FakeAI) -> None:
    workspace_id = workspace_with_sales(client)
    fake_ai.answer = (
        "```sql\nSELECT city, SUM(amount) AS total FROM sales GROUP BY city "
        "ORDER BY total DESC\n```"
    )

    response = ask(client, workspace_id, "  Total amount by city  ")

    assert response.status_code == 200
    body = response.json()
    assert body["columns"] == ["city", "total"]
    assert body["rows"] == [["Brno", 250], ["Prague", 180]]
    assert body["row_count"] == 2
    assert body["truncated"] is False
    assert body["sql"].endswith("LIMIT 1000")  # the real limit, not the internal +1 probe
    assert body["sql"].startswith("SELECT\n")  # laid out on lines for reading

    prompt = fake_ai.prompts[0]
    assert '"city" TEXT  (original name: "City")' in prompt
    assert '(original name: "Amount ($)")' in prompt
    assert prompt.endswith("Question: Total amount by city")  # trimmed


def test_dangerous_sql_from_ai_is_blocked(client: TestClient, fake_ai: FakeAI) -> None:
    workspace_id = workspace_with_sales(client)
    fake_ai.answer = "DROP TABLE sales"

    response = ask(client, workspace_id, "delete everything")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "SQL_NOT_ALLOWED"
    assert response.json()["error"]["sql"] == "DROP TABLE sales"

    fake_ai.answer = "SELECT COUNT(*) AS n FROM sales"
    assert ask(client, workspace_id, "how many rows").json()["rows"] == [[3]]


def test_cannot_answer(client: TestClient, fake_ai: FakeAI) -> None:
    workspace_id = workspace_with_sales(client)
    fake_ai.answer = "CANNOT_ANSWER: no weather data"

    response = ask(client, workspace_id, "what is the weather")
    assert response.status_code == 422
    assert response.json()["error"] == {"code": "AI_ERROR", "message": "no weather data"}


def test_broken_sql_from_ai(client: TestClient, fake_ai: FakeAI) -> None:
    workspace_id = workspace_with_sales(client)
    fake_ai.answer = "SELECT no_such_column FROM sales"

    response = ask(client, workspace_id, "?")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "SQL_EXECUTION_ERROR"
    assert response.json()["error"]["sql"] == "SELECT no_such_column FROM sales"


def test_workspace_without_tables(client: TestClient, fake_ai: FakeAI) -> None:
    workspace_id = client.post("/api/workspaces").json()["workspace_id"]
    response = ask(client, workspace_id, "anything")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_REQUEST"
    assert fake_ai.prompts == []  # no AI call wasted


def test_unknown_workspace(client: TestClient, fake_ai: FakeAI) -> None:
    response = ask(client, "00000000-0000-0000-0000-000000000000", "q")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "WORKSPACE_NOT_FOUND"
    assert "sql" not in response.json()["error"]  # only errors about generated SQL carry it


@pytest.mark.parametrize(
    "body", [{"question": ""}, {"question": "   "}, {}, {"question": "x" * 2001}]
)
def test_invalid_question(client: TestClient, fake_ai: FakeAI, body: dict) -> None:
    workspace_id = workspace_with_sales(client)
    response = client.post(f"/api/workspaces/{workspace_id}/query", json=body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_ai_not_configured(client: TestClient) -> None:
    # No fake: the real factory runs with the test settings, which have no API key.
    workspace_id = workspace_with_sales(client)
    response = ask(client, workspace_id, "q")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "AI_ERROR"
    assert "AI_API_KEY" in response.json()["error"]["message"]
