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


class AppError(Exception):
    def __init__(self, code: ErrorCode, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def _error_response(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return _error_response(exc.code, exc.message, exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = "; ".join(
            f"{'.'.join(str(part) for part in err['loc'])}: {err['msg']}" for err in exc.errors()
        )
        return _error_response(ErrorCode.INVALID_REQUEST, details, 422)
