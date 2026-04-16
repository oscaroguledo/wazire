from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError
from typing import Union
from core.utils.logger import logger
from core.utils.response import Response


class AppError(Exception):
    """Base exception for application errors."""
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR, details: dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(AppError):
    """Resource not found error."""
    def __init__(self, message: str = "Resource not found", details: dict = None):
        super().__init__(message, status.HTTP_404_NOT_FOUND, details)


class BadRequestError(AppError):
    """Bad request error."""
    def __init__(self, message: str = "Bad request", details: dict = None):
        super().__init__(message, status.HTTP_400_BAD_REQUEST, details)


class UnauthorizedError(AppError):
    """Unauthorized error."""
    def __init__(self, message: str = "Unauthorized", details: dict = None):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED, details)


class ForbiddenError(AppError):
    """Forbidden error."""
    def __init__(self, message: str = "Forbidden", details: dict = None):
        super().__init__(message, status.HTTP_403_FORBIDDEN, details)


class ConflictError(AppError):
    """Conflict error."""
    def __init__(self, message: str = "Conflict", details: dict = None):
        super().__init__(message, status.HTTP_409_CONFLICT, details)


def setup_error_handlers(app: FastAPI):
    """Setup centralized error handlers for the FastAPI app."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        """Handle custom application errors."""
        logger.error(f"AppError: {exc.message} - Path: {request.url.path}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": exc.message,
                "details": exc.details if exc.details else None
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        """Handle Pydantic validation errors."""
        # Convert errors to serializable format
        errors = []
        for error in exc.errors():
            error_dict = dict(error)
            # Convert any non-serializable values to strings
            if 'ctx' in error_dict and isinstance(error_dict['ctx'], dict):
                for key, value in error_dict['ctx'].items():
                    if not isinstance(value, (str, int, float, bool, list, dict, type(None))):
                        error_dict['ctx'][key] = str(value)
            errors.append(error_dict)
        
        logger.warning(f"Validation error: {errors} - Path: {request.url.path}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": "Validation error",
                "details": errors
            }
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error_handler(request: Request, exc: SQLAlchemyError):
        """Handle database errors."""
        logger.error(f"Database error: {str(exc)} - Path: {request.url.path}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": "Database error occurred",
                "details": None  # Don't expose database details in production
            }
        )

    @app.exception_handler(Exception)
    async def general_error_handler(request: Request, exc: Exception):
        """Handle all other exceptions."""
        logger.error(f"Unhandled exception: {str(exc)} - Path: {request.url.path}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": "An unexpected error occurred",
                "details": None
            }
        )
