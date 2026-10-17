"""Typed domain exceptions for the DevSquad LangGraph orchestration layer."""

from typing import Any, Optional
from app.core.exceptions import DevSquadException


class OrchestrationError(DevSquadException):
    """Base exception for all workflow orchestration errors."""
    pass


class StateTransitionError(OrchestrationError):
    """Raised when an invalid state transition or routing decision is attempted."""
    pass


class CheckpointError(OrchestrationError):
    """Raised when checkpoint serialization, saving, or retrieval fails."""
    pass


class RunNotResumableError(OrchestrationError):
    """Raised when attempting to resume a run that is terminal, corrupted, or not resumable."""
    pass


class UnauthorizedRunAccessError(OrchestrationError):
    """Raised when access to a run or thread violates authorization or tenant boundaries."""
    pass
