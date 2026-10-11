from dataclasses import asdict

from fastapi import APIRouter, Depends, File, UploadFile

from app.config import Settings, get_settings
from app.errors import AppError, ErrorCode
from app.models.schemas import UploadedTable, UploadResponse
from app.services import ingest_service, workspace_service

router = APIRouter(prefix="/workspaces", tags=["files"])


@router.post("/{workspace_id}/files", response_model=UploadResponse)
def upload_files(
    workspace_id: str,
    files: list[UploadFile] = File(...),
    settings: Settings = Depends(get_settings),
) -> UploadResponse:
    db_path = workspace_service.get_db_path(settings.data_dir, workspace_id)

    uploaded = []
    for file in files:
        filename = file.filename or "file"
        # Read one byte past the limit to detect oversized files without loading them fully.
        content = file.file.read(settings.max_upload_bytes + 1)
        if len(content) > settings.max_upload_bytes:
            raise AppError(
                ErrorCode.INVALID_FILE,
                f"'{filename}': file exceeds {settings.max_upload_mb} MB limit",
                413,
            )
        uploaded.append(ingest_service.UploadedFile(filename=filename, content=content))

    tables = ingest_service.ingest_files(db_path, uploaded)
    return UploadResponse(tables=[UploadedTable.model_validate(asdict(t)) for t in tables])
