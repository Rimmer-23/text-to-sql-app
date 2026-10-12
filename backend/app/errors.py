from enum import StrEnum

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ErrorCode(StrEnum):
    INVALID_FILE = "INVALID_FILE"
    INVALID_REQUEST = "INVALID_REQUEST"
    SQL_NOT_ALLOWED = "SQL_NOT_ALLOWED"
    SQL_EXECUTION_ERROR = "SQL_EXECUTION_ERROR"
    AI_ERROR = "AI_ERROR"
    WORKSPACE_NOT_FOUND = "WORKSPACE_NOT_FOUND"
    TABLE_NOT_FOUND = "TABLE_NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppError(Exception):
    def __init__(self, code: ErrorCode, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        # The SQL the AI generated, when the error is about that SQL, so the user can see it.
        self.sql: str | None = None


def _error_response(
    code: str, message: str, status_code: int, sql: str | None = None
) -> JSONResponse:
    error: dict[str, str] = {"code": code, "message": message}
    if sql is not None:
        error["sql"] = sql
    return JSONResponse(status_code=status_code, content={"error": error})


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return _error_response(exc.code, exc.message, exc.status_code, exc.sql)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = "; ".join(
            f"{'.'.join(str(part) for part in err['loc'])}: {err['msg']}" for err in exc.errors()
        )
        return _error_response(ErrorCode.INVALID_REQUEST, details, 422)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        # Keeps the error format even for bugs. Starlette still re-raises the exception after
        # this response, so the full traceback lands in the backend terminal.
        return _error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Unexpected server error ({type(exc).__name__}). "
            "Details are in the terminal where the backend runs.",
            500,
        )
