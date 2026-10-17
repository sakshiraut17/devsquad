"""DevSquad core exception hierarchy."""
from typing import Any, Optional


class DevSquadException(Exception):
    """Base exception for all DevSquad domain errors."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(DevSquadException):
    """Raised when application configuration is invalid or missing."""


class DatabaseError(DevSquadException):
    """Raised when a database error occurs."""


class EntityNotFoundError(DevSquadException):
    """Raised when a requested entity does not exist in persistence."""


class EntityConflictError(DevSquadException):
    """Raised when an entity uniqueness constraint is violated."""


class SecurityViolationError(DevSquadException):
    """Raised when an operation violates security rules (e.g. path traversal, secret leak)."""


class WorkflowStateError(DevSquadException):
    """Raised when an invalid state transition or operation occurs."""


class ValidationFailedError(DevSquadException):
    """Raised when input or patch validation fails."""


# Alias for convenience
ValidationError = ValidationFailedError
