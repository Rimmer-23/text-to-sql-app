from dataclasses import asdict

from fastapi import APIRouter, Depends

from app.ai.base import AIProvider
from app.ai.factory import get_ai_provider
from app.config import Settings, get_settings
from app.errors import AppError, ErrorCode
from app.models.schemas import QueryRequest, QueryResponse
from app.services import query_service, schema_service, workspace_service

router = APIRouter(prefix="/workspaces", tags=["query"])


@router.post("/{workspace_id}/query", response_model=QueryResponse)
def ask_question(
    workspace_id: str,
    request: QueryRequest,
    settings: Settings = Depends(get_settings),
    ai: AIProvider = Depends(get_ai_provider),
) -> QueryResponse:
    db_path = workspace_service.get_db_path(settings.data_dir, workspace_id)
    tables = schema_service.get_schema(db_path)
    if not tables:
        raise AppError(
            ErrorCode.INVALID_REQUEST, "Upload at least one file before asking questions", 400
        )

    sql = ai.generate_sql(tables, request.question)
    try:
        result = query_service.run_query(
            db_path,
            sql,
            max_rows=settings.max_result_rows,
            timeout_seconds=settings.query_timeout_seconds,
        )
    except AppError as exc:
        exc.sql = sql  # show the user what the AI wrote when it is blocked or fails
        raise
    return QueryResponse.model_validate(asdict(result))
