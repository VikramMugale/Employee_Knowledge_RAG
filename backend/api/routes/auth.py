"""
JWT login and current-user endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from backend.auth.models import LoginRequest, TokenResponse, UserProfile, UserContext
from backend.auth.authentication import auth_service, AuthenticationError, ROLE_ACCESS
from backend.api.dependencies import get_current_user_context
from backend.config.settings import settings

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    """Authenticate with email/password and return a signed JWT."""
    try:
        user = auth_service.authenticate_credentials(payload.email, payload.password)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    token = auth_service.issue_token(user)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.jwt_expire_minutes * 60,
        user=user,
    )


@router.get("/me", response_model=UserProfile)
async def me(user_context: UserContext = Depends(get_current_user_context)):
    """Return the authenticated user profile from the verified JWT."""
    user = auth_service.user_from_context(user_context)
    return UserProfile(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        department=user.department,
        location=user.location,
        employment_type=user.employment_type,
        allowed_access_levels=user_context.allowed_access_levels or ROLE_ACCESS.get(user.role, ["PUBLIC_INTERNAL"]),
    )
