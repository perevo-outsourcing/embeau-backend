"""Custom exceptions for the EMBEAU API."""

from typing import Any


class EmbeauException(Exception):
    """Base exception for EMBEAU API."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class AuthenticationError(EmbeauException):
    """Authentication failed."""

    def __init__(self, message: str = "Authentication failed", details: dict[str, Any] | None = None) -> None:
        super().__init__(message, "AUTH_ERROR", details)


class AuthorizationError(EmbeauException):
    """User not authorized for this action."""

    def __init__(self, message: str = "Not authorized", details: dict[str, Any] | None = None) -> None:
        super().__init__(message, "FORBIDDEN", details)


class NotFoundError(EmbeauException):
    """Resource not found."""

    def __init__(self, resource: str, identifier: str | None = None) -> None:
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} with id '{identifier}' not found"
        super().__init__(message, "NOT_FOUND", {"resource": resource, "identifier": identifier})


class ValidationError(EmbeauException):
    """Validation failed."""

    def __init__(self, message: str, field: str | None = None) -> None:
        details = {"field": field} if field else {}
        super().__init__(message, "VALIDATION_ERROR", details)


class ExternalServiceError(EmbeauException):
    """External service call failed."""

    def __init__(self, service: str, message: str) -> None:
        super().__init__(
            f"External service '{service}' failed: {message}",
            "EXTERNAL_SERVICE_ERROR",
            {"service": service},
        )


class ColorAnalysisError(EmbeauException):
    """Color analysis failed."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, "COLOR_ANALYSIS_ERROR", details)


class EmotionAnalysisError(EmbeauException):
    """Emotion analysis failed."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, "EMOTION_ANALYSIS_ERROR", details)
