"""Pydantic V2 schemas for human approval decisions."""
from datetime import datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class ApprovalRequest(BaseModel):
    """Payload submitted by a human maintainer to approve or reject a patch."""
    model_config = ConfigDict(extra="forbid")

    patch_id: str = Field(..., description="ID of the patch revision being reviewed")
    decision: Literal["approved", "rejected"] = Field(..., description="Human decision")
    patch_hash: str = Field(..., description="Exact SHA-256 hash of the presented patch content")
    base_commit_sha: Optional[str] = Field(default=None, description="Optional target base commit SHA to verify")
    feedback: Optional[str] = Field(default=None, description="Optional maintainer notes or rejection reasons")


class ApprovalResponse(BaseModel):
    """Persisted audit response confirming recorded human approval."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    patch_id: str
    approver_id: Optional[str] = None
    decision: str
    patch_hash: str
    validation_evidence: dict[str, Any]
    feedback: Optional[str] = None
    created_at: datetime
