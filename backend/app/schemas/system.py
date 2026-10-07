from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Simple health check status response."""

    status: str = Field(default="healthy", json_schema_extra={"example": "healthy"})
    project: str = Field(..., json_schema_extra={"example": "DevSquad AI Engineering Platform"})
    version: str = Field(..., json_schema_extra={"example": "0.1.0"})
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SystemStatusResponse(BaseModel):
    """Detailed system diagnostic status response."""

    status: str = Field(..., json_schema_extra={"example": "operational"})
    environment: str = Field(..., json_schema_extra={"example": "development"})
    version: str = Field(..., json_schema_extra={"example": "0.1.0"})
    database_connected: bool = Field(..., json_schema_extra={"example": True})
    database_engine: str = Field(..., json_schema_extra={"example": "sqlite+aiosqlite"})
    llm_provider: str = Field(..., json_schema_extra={"example": "gemini"})
    llm_configured: bool = Field(..., json_schema_extra={"example": True})
    docker_available: bool = Field(..., json_schema_extra={"example": False})
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = Field(default_factory=dict)
