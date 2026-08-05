"""Unified error model (Band 10: every error returns code, message, details, correlation_id).

Domain and application code raises `DomainError` subclasses; the presentation
layer (see app/main.py) translates them into this consistent HTTP error body.
It never leaks stack traces or infrastructure details to the client.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None
    correlation_id: str


class DomainError(Exception):
    """Base class for all business-rule violations raised by domain/application code."""

    code: str = "domain_error"
    http_status: int = 400

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class NotFoundError(DomainError):
    code = "not_found"
    http_status = 404


class ValidationError(DomainError):
    code = "validation_error"
    http_status = 422


class ConflictError(DomainError):
    code = "conflict"
    http_status = 409


class UnauthorizedError(DomainError):
    code = "unauthorized"
    http_status = 401


class ForbiddenError(DomainError):
    code = "forbidden"
    http_status = 403


class RateLimitedError(DomainError):
    code = "rate_limited"
    http_status = 429
