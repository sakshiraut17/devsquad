"""Pydantic V2 schemas for Run execution."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.db.models.run import RunStatus


class RunCreate(BaseModel):
    """Payload to trigger an execution run for an ingested issue."""
    model_config = ConfigDict(extra="forbid")

    repository_id: str = Field(..., description="Target repository ID")
    issue_id: str = Field(..., description="Target issue ID")


class RunResponse(BaseModel):
    """Response representation of an execution run."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    repository_id: str
    issue_id: str
    status: RunStatus
    current_node: str
    retry_count: int
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime
