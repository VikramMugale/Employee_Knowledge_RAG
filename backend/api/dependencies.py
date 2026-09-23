"""
FastAPI route dependency injection utilities for authentication and user context.
"""

from typing import Optional
from fastapi import Header, HTTPException, status, Depends
from backend.auth.models import UserContext, Role
from backend.auth.authentication import auth_service, AuthenticationError


async def get_current_user_context(
    authorization: Optional[str] = Header(default=None),
) -> UserContext:
    """Dependency extracting user identity and security context from Authorization header."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return auth_service.authenticate_token(authorization)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def require_admin(
    user_context: UserContext = Depends(get_current_user_context),
) -> UserContext:
    """Authorize admin access only."""
    if user_context.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required.",
        )
    return user_context
