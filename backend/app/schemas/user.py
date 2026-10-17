"""Pydantic V2 schemas for User management."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Payload to register a new user."""
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(..., description="User's unique email address")
    display_name: str = Field(..., min_length=2, max_length=255, description="Maintainer display name")


class UserResponse(BaseModel):
    """User account response representation."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    display_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
