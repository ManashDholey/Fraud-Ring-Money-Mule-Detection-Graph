"""
Error Response DTOs and Exception Handling
Provides structured, sanitized error responses that don't leak internal details.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from enum import Enum


class ErrorCode(str, Enum):
    """Standardized error codes for API responses."""
    INTERNAL_ERROR = "INTERNAL_ERROR"
    NOT_FOUND = "NOT_FOUND"
    INVALID_REQUEST = "INVALID_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    VALIDATION_ERROR = "VALIDATION_ERROR"


class ErrorResponseDTO(BaseModel):
    """
    Structured error response DTO.
    Provides safe, client-friendly error information without leaking internals.
    """
    error: Dict[str, Any] = Field(
        ...,
        description="Error details with code and user-friendly message"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Something went wrong while processing your request. Please try again."
                }
            }
        }


def create_error_response(
    code: ErrorCode,
    message: str,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a structured error response that's safe to send to clients.
    Never includes raw exception text, stack traces, or database-specific error codes.
    """
    response = {
        "error": {
            "code": code.value,
            "message": message
        }
    }
    
    if request_id:
        response["error"]["request_id"] = request_id
    
    return response


class CustomException(Exception):
    """Base exception class for application-specific errors."""
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int = 500,
        internal_error: Optional[Exception] = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.internal_error = internal_error
        super().__init__(self.message)
