from dataclasses import asdict

from fastapi import APIRouter, Depends, status

from app.config import Settings, get_settings
from app.models.schemas import SchemaResponse, TableSchema, WorkspaceCreated
from app.services import schema_service, workspace_service

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceCreated, status_code=status.HTTP_201_CREATED)
def create_workspace(settings: Settings = Depends(get_settings)) -> WorkspaceCreated:
    workspace_id = workspace_service.create_workspace(settings.data_dir)
    return WorkspaceCreated(workspace_id=workspace_id)


@router.get("/{workspace_id}/schema", response_model=SchemaResponse)
def get_schema(workspace_id: str, settings: Settings = Depends(get_settings)) -> SchemaResponse:
    db_path = workspace_service.get_db_path(settings.data_dir, workspace_id)
    tables = schema_service.get_schema(db_path)
    return SchemaResponse(
        workspace_id=workspace_id,
        tables=[TableSchema.model_validate(asdict(table)) for table in tables],
    )
