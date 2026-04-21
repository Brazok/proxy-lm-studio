"""Application exception hierarchy."""

from __future__ import annotations


class AppError(Exception):
    """Root exception for all application errors."""

    default_message: str = "Application error"

    def __init__(
        self,
        message: str | None = None,
        *,
        context: dict[str, object] | None = None,
    ) -> None:
        """Initialize with an optional message and context dict.

        Args:
            message: Human-readable error description. Falls back to default_message.
            context: Arbitrary key/value pairs for structured logging.
        """
        super().__init__(message or self.default_message)
        self.context: dict[str, object] = context or {}


class RouteError(AppError):
    """Raised when route matching fails unexpectedly."""

    default_message = "Route matching error"


class FileServeError(AppError):
    """Raised when a mock response file cannot be read or resolved."""

    default_message = "File serve error"


class ConfigurationError(AppError):
    """Raised when configuration is invalid at startup."""

    default_message = "Configuration error"
