from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app
from app.services import workspace_service


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    # Explicit values win over backend/.env and env vars, so tests never pick up a real API
    # key and never call a real AI provider.
    return Settings(
        _env_file=None, data_dir=tmp_path / "data", max_upload_mb=1, ai_api_key="", ai_model=""
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def db_path(settings: Settings) -> Path:
    workspace_id = workspace_service.create_workspace(settings.data_dir)
    return workspace_service.get_db_path(settings.data_dir, workspace_id)
