"""OAuth login and current-user endpoints. Password login is disabled."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from backend.auth.models import TokenResponse, UserProfile, UserContext
from backend.auth.authentication import auth_service, AuthenticationError, ROLE_ACCESS
from backend.auth.oauth import authorization_url, exchange_code, frontend_redirect, oauth_configured, provider_name
from backend.api.dependencies import get_current_user_context
from backend.config.settings import settings

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/oauth/status")
async def oauth_status():
    return {"configured": oauth_configured(), "provider": provider_name(), "login_url": "/api/v1/auth/oauth/login"}


@router.get("/oauth/login")
async def oauth_login():
    try:
        url, state = authorization_url()
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    response = RedirectResponse(url=url, status_code=302)
    response.set_cookie("oauth_state", state, httponly=True, samesite="lax", max_age=600, secure=settings.environment == "production")
    return response


@router.get("/oauth/callback")
async def oauth_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    if error:
        return RedirectResponse(frontend_redirect(error=error), status_code=302)
    cookie_state = request.cookies.get("oauth_state")
    if not code:
        return RedirectResponse(frontend_redirect(error="missing_code"), status_code=302)
    if cookie_state and state and cookie_state != state:
        return RedirectResponse(frontend_redirect(error="invalid_state"), status_code=302)
    try:
        user = await exchange_code(code)
        token = auth_service.issue_token(user)
    except AuthenticationError as exc:
        return RedirectResponse(frontend_redirect(error=str(exc)), status_code=302)
    response = RedirectResponse(frontend_redirect(token=token), status_code=302)
    response.delete_cookie("oauth_state")
    return response


@router.post("/login", response_model=TokenResponse)
async def login():
    raise HTTPException(status_code=status.HTTP_410_GONE, detail="Password login is disabled. Use /api/v1/auth/oauth/login.")


@router.get("/me", response_model=UserProfile)
async def me(user_context: UserContext = Depends(get_current_user_context)):
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
