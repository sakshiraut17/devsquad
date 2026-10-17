"""Pydantic V2 schemas for system health and diagnostics."""
from datetime import datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

ComponentStatus = Literal["operational", "degraded", "unavailable", "unconfigured", "error"]


class ComponentHealth(BaseModel):
    """Health status and diagnostic details of an individual subsystem."""
    model_config = ConfigDict(extra="forbid")

    component: str = Field(..., description="Name of the component, e.g. 'database', 'llm', 'docker'")
    status: ComponentStatus = Field(..., description="Honest health status")
    message: str = Field(..., description="Actionable descriptive explanation")
    details: dict[str, Any] = Field(default_factory=dict, description="Diagnostic telemetry (secrets redacted)")
    checked_at: datetime = Field(..., description="Timestamp of health verification")


class HealthResponse(BaseModel):
    """Composite health response aggregating all core subsystems."""
    model_config = ConfigDict(extra="forbid")

    status: ComponentStatus = Field(..., description="Overall platform status")
    environment: str = Field(..., description="Deployment environment")
    version: str = Field(default="0.1.0", description="Backend service version")
    components: dict[str, ComponentHealth] = Field(..., description="Subsystem health map")
    timestamp: datetime = Field(..., description="Response generation timestamp")
