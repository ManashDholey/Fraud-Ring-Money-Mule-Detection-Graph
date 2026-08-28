"""
Centralized Exception Handlers
Provides consistent, sanitized error responses across all endpoints.
Logs full error details server-side while returning safe messages to clients.
"""

import logging
from typing import Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from neo4j.exceptions import Neo4jError

from dto.error import (
    ErrorCode,
    ErrorResponseDTO,
    create_error_response,
    CustomException
)

logger = logging.getLogger(__name__)


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all exception handler for unexpected errors.
    Logs full error details server-side, returns generic safe message to client.
    """
    # Extract request ID if available for correlation
    request_id = request.headers.get("X-Request-ID", "unknown")
    
    # Log FULL exception details server-side for debugging
    logger.error(
        f"Unhandled exception for request {request_id}: {type(exc).__name__}",
        exc_info=exc,
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc)
        }
    )
    
    # Return generic, sanitized response to client
    response = create_error_response(
        code=ErrorCode.INTERNAL_ERROR,
        message="Something went wrong while processing your request. Please try again.",
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response
    )


async def neo4j_exception_handler(request: Request, exc: Neo4jError) -> JSONResponse:
    """
    Specific handler for Neo4j/CognoDB exceptions.
    Database errors are typically 503 (Service Unavailable) for connectivity issues,
    or 500 for actual query bugs, but client never sees the raw error.
    """
    request_id = request.headers.get("X-Request-ID", "unknown")
    
    # Log FULL Neo4j error details server-side
    logger.error(
        f"Neo4j/Database error for request {request_id}",
        exc_info=exc,
        extra={
            "path": request.url.path,
            "method": request.method,
            "neo4j_code": getattr(exc, "code", "UNKNOWN"),
            "neo4j_message": str(exc),
            "exception_type": type(exc).__name__
        }
    )
    
    # Determine appropriate HTTP status based on error type
    if "connection" in str(exc).lower() or "timeout" in str(exc).lower():
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        message = "Database connection issue. Please try again in a moment."
    else:
        # For query errors, general database errors, etc.
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        message = "Something went wrong while processing your request. Please try again."
    
    response = create_error_response(
        code=ErrorCode.SERVICE_UNAVAILABLE if status_code == 503 else ErrorCode.INTERNAL_ERROR,
        message=message,
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=status_code,
        content=response
    )


async def custom_exception_handler(request: Request, exc: CustomException) -> JSONResponse:
    """Handler for application-specific CustomException errors."""
    request_id = request.headers.get("X-Request-ID", "unknown")
    
    # Log at appropriate level
    if exc.status_code >= 500:
        logger.error(
            f"Application error for request {request_id}: {exc.code.value}",
            exc_info=exc.internal_error if exc.internal_error else exc,
            extra={
                "path": request.url.path,
                "method": request.method,
                "error_code": exc.code.value,
                "message": exc.message
            }
        )
    else:
        logger.warning(
            f"Client error for request {request_id}: {exc.code.value}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "error_code": exc.code.value,
                "message": exc.message
            }
        )
    
    response = create_error_response(
        code=exc.code,
        message=exc.message,
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response
    )


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handler for validation/value errors."""
    request_id = request.headers.get("X-Request-ID", "unknown")
    
    logger.warning(
        f"Validation error for request {request_id}: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_message": str(exc)
        }
    )
    
    response = create_error_response(
        code=ErrorCode.VALIDATION_ERROR,
        message="The provided data is invalid. Please check your input and try again.",
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=response
    )
