from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class RepositoryResponse(BaseModel):
    """Repository metadata response schema."""

    id: Optional[str] = None
    full_name: str = Field(..., json_schema_extra={"example": "octocat/Hello-World"})
    default_branch: str = Field(default="main", json_schema_extra={"example": "main"})
    is_active: bool = Field(default=True)
    description: Optional[str] = None
    stars_count: int = Field(default=0)
    open_issues_count: int = Field(default=0)
    connected_at: Optional[datetime] = None


class IssueResponse(BaseModel):
    """GitHub Issue response schema."""

    id: Optional[str] = None
    issue_number: int = Field(..., json_schema_extra={"example": 42})
    title: str = Field(..., json_schema_extra={"example": "Fix KeyError on missing token in auth header"})
    body: Optional[str] = Field(default="", json_schema_extra={"example": "When token is absent, raises uncaught KeyError."})
    state: str = Field(default="open", json_schema_extra={"example": "open"})
    author: Optional[str] = None
    labels: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    synced_at: Optional[datetime] = None


class FileTreeNode(BaseModel):
    """File tree node for repository structure inspection."""

    path: str = Field(..., json_schema_extra={"example": "src/core/auth.py"})
    type: str = Field(..., json_schema_extra={"example": "blob"})  # "blob" or "tree"
    size: Optional[int] = Field(default=0)


class FileContentResponse(BaseModel):
    """Repository file content retrieval response."""

    path: str = Field(..., json_schema_extra={"example": "src/core/auth.py"})
    content: str = Field(..., json_schema_extra={"example": "def authenticate(token):\n    ..."})
    size: int = Field(default=0)
    truncated: bool = Field(default=False)


class ConnectRepositoryRequest(BaseModel):
    """Request payload to connect and index a GitHub repository."""

    full_name: str = Field(..., json_schema_extra={"example": "owner/repository"})
