"""Pydantic V2 schemas for Issue management."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class IssueCreate(BaseModel):
    """Payload to persist an ingested issue."""
    model_config = ConfigDict(extra="forbid")

    repository_id: str = Field(..., description="DevSquad internal repository ID")
    github_issue_number: int = Field(..., gt=0, description="GitHub issue number")
    title: str = Field(..., min_length=1, max_length=500)
    body: Optional[str] = Field(default=None)
    state: str = Field(default="open")
    labels: list[str] = Field(default_factory=list)
    html_url: Optional[str] = Field(default=None)


class IssueResponse(BaseModel):
    """Response representation for an ingested issue."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    repository_id: str
    github_issue_number: int
    title: str
    body: Optional[str]
    state: str
    labels: list[str]
    html_url: Optional[str]
    created_at: datetime
    updated_at: datetime
    last_synced_at: datetime
