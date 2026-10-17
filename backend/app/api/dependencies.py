"""FastAPI authentication and authorization dependencies."""
from typing import Optional
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_access_token
from app.db.models.repository import Repository
from app.db.models.run import Run
from app.db.models.user import User
from app.db.session import get_db

oauth2_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate Bearer access token from Authorization header and resolve active authenticated User."""
    raw_token: Optional[str] = None
    if credentials and credentials.scheme.lower() == "bearer":
        raw_token = credentials.credentials

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided or invalid.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = verify_access_token(raw_token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired authentication token: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject identifier.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_authorized_repository(
    repository_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Repository:
    """Verify repository exists and caller is authorized to access it."""
    repo = await db.get(Repository, repository_id)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository '{repository_id}' not found.",
        )

    # Check ownership: if owner_id is set, it must match current_user.id
    if repo.owner_id is not None and repo.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to access this repository.",
        )

    return repo


async def get_authorized_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Run:
    """Verify run exists and caller is authorized to access its repository."""
    run = await db.get(Run, run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow run '{run_id}' not found.",
        )

    repo = await db.get(Repository, run.repository_id)
    if repo and repo.owner_id is not None and repo.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to access this execution run.",
        )

    return run


async def get_stream_authorized_run(
    run_id: str,
    ticket: Optional[str] = Query(default=None),
    token: Optional[str] = Query(default=None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Run:
    """
    Authenticate and authorize access to SSE telemetry stream.
    Accepts:
    1. Short-lived signed stream ticket (?ticket=...) with replay protection.
    2. Standard Authorization: Bearer header.
    Explicitly rejects long-lived bearer tokens passed via ?token=... to prevent URL exposure.
    """
    if token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Passing bearer tokens in query parameter 'token' is prohibited for security reasons. Acquire a short-lived ticket via POST /api/v1/runs/{id}/stream-ticket and pass ?ticket=...",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: Optional[str] = None
    if ticket:
        from app.core.security import verify_stream_ticket
        try:
            payload = verify_stream_ticket(ticket=ticket, expected_run_id=run_id, consume=True)
            user_id = payload.get("sub")
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid or expired stream ticket: {str(exc)}",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
    elif credentials and credentials.scheme.lower() == "bearer":
        try:
            payload = verify_access_token(credentials.credentials)
            user_id = payload.get("sub")
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid or expired authentication token: {str(exc)}",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials not provided. Provide a valid 'ticket' query parameter or Authorization Bearer header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject identifier.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    run = await db.get(Run, run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow run '{run_id}' not found.",
        )

    repo = await db.get(Repository, run.repository_id)
    if repo and repo.owner_id is not None and repo.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to access this execution run.",
        )

    return run

