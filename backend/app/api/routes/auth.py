"""Authentication and session management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.security import create_access_token
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


class SessionRequest(BaseModel):
    """Payload to establish maintainer session."""
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(default="maintainer@devsquad.ai", description="Maintainer email")
    display_name: str = Field(default="DevSquad Maintainer", description="Display name")


class TokenResponse(BaseModel):
    """Access token response schema."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Retrieve currently authenticated maintainer profile."""
    return current_user


@router.post("/session", response_model=TokenResponse)
async def create_session(
    payload: SessionRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate or auto-provision maintainer session and issue signed Bearer token."""
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user:
        from app.core.config import settings
        if settings.env == "production":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Demo self-provisioning via /auth/session is disabled in production.",
            )
        user = User(
            email=payload.email,
            display_name=payload.display_name,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    token = create_access_token(user_id=user.id, email=user.email)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )
