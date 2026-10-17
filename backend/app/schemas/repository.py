"""Pydantic V2 schemas for Repository management."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class RepositoryCreate(BaseModel):
    """Payload to register a monitored repository."""
    model_config = ConfigDict(extra="forbid")

    github_repository_id: int = Field(..., gt=0, description="GitHub numerical repository ID")
    full_name: str = Field(..., pattern=r"^[a-zA-Z0-9_\-\.]+/[a-zA-Z0-9_\-\.]+$", description="Owner/repo full name")
    default_branch: str = Field(default="main", min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=2000)
    owner_id: Optional[str] = Field(default=None, description="DevSquad user ID of repository owner")


class RepositoryResponse(BaseModel):
    """Response representation for a registered repository."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: Optional[str]
    github_repository_id: int
    full_name: str
    default_branch: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
