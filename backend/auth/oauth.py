"""OAuth 2.0 authorization-code login for Google, Microsoft Entra ID, or generic OIDC."""
from __future__ import annotations
from typing import Dict, Optional, Tuple
from urllib.parse import urlencode
import secrets
import httpx
import jwt
from backend.auth.authentication import AuthenticationError
from backend.auth.models import Role, User
from backend.config.logging import logger
from backend.config.settings import settings

PROVIDERS = {
    "google": {
        "authorize": "https://accounts.google.com/o/oauth2/v2/auth",
        "token": "https://oauth2.googleapis.com/token",
        "userinfo": "https://openidconnect.googleapis.com/v1/userinfo",
        "scope": "openid email profile",
    },
    "microsoft": {
        "authorize": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
        "token": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
        "userinfo": "https://graph.microsoft.com/oidc/userinfo",
        "scope": "openid email profile User.Read",
    },
}

def provider_name() -> str:
    return (settings.oauth_provider or "google").strip().lower()

def _tenant() -> str:
    return settings.oauth_tenant or "common"

def _endpoints() -> Dict[str, str]:
    name = provider_name()
    if name == "oidc":
        return {
            "authorize": settings.oauth_authorize_url,
            "token": settings.oauth_token_url,
            "userinfo": settings.oauth_userinfo_url,
            "scope": settings.oauth_scope or "openid email profile",
        }
    preset = PROVIDERS.get(name)
    if not preset:
        raise AuthenticationError(f"Unsupported OAuth provider: {name}")
    return {
        "authorize": preset["authorize"].format(tenant=_tenant()),
        "token": preset["token"].format(tenant=_tenant()),
        "userinfo": preset["userinfo"],
        "scope": settings.oauth_scope or preset["scope"],
    }

def oauth_configured() -> bool:
    return bool(settings.oauth_client_id and settings.oauth_client_secret and settings.oauth_redirect_uri)

def authorization_url() -> Tuple[str, str]:
    if not oauth_configured():
        raise AuthenticationError("OAuth is not configured. Set OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET, and OAUTH_REDIRECT_URI.")
    endpoints = _endpoints()
    if not endpoints["authorize"]:
        raise AuthenticationError("OAuth authorize URL is missing.")
    state = secrets.token_urlsafe(24)
    params = {
        "client_id": settings.oauth_client_id,
        "redirect_uri": settings.oauth_redirect_uri,
        "response_type": "code",
        "scope": endpoints["scope"],
        "state": state,
        "prompt": "select_account",
    }
    return f"{endpoints['authorize']}?{urlencode(params)}", state

def _admin_emails() -> set:
    raw = settings.oauth_admin_emails or ""
    return {item.strip().lower() for item in raw.split(",") if item.strip()}

def _role_for_email(email: str, claims: Dict) -> Role:
    lowered = (email or "").lower()
    if lowered in _admin_emails():
        return Role.ADMIN
    groups = claims.get("groups") or claims.get("roles") or []
    if isinstance(groups, str):
        groups = [groups]
    joined = " ".join(str(item).lower() for item in groups)
    if "admin" in joined:
        return Role.ADMIN
    return Role.EMPLOYEE

def user_from_claims(claims: Dict) -> User:
    email = (claims.get("email") or claims.get("preferred_username") or claims.get("upn") or "").strip()
    if not email:
        raise AuthenticationError("OAuth provider did not return an email address.")
    name = claims.get("name") or claims.get("given_name") or email.split("@")[0]
    role = _role_for_email(email, claims)
    subject = str(claims.get("sub") or claims.get("oid") or email)
    return User(
        id=f"oauth_{subject}"[:64],
        email=email,
        full_name=str(name),
        role=role,
        department=str(claims.get("department") or "General"),
        location="Global",
        employment_type="full_time",
    )

async def exchange_code(code: str) -> User:
    endpoints = _endpoints()
    data = {
        "client_id": settings.oauth_client_id,
        "client_secret": settings.oauth_client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": settings.oauth_redirect_uri,
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        token_response = await client.post(endpoints["token"], data=data, headers={"Accept": "application/json"})
        if token_response.status_code >= 400:
            logger.warning("[OAUTH] token exchange failed: %s %s", token_response.status_code, token_response.text[:300])
            raise AuthenticationError("OAuth token exchange failed.")
        tokens = token_response.json()
        claims: Dict = {}
        id_token = tokens.get("id_token")
        if id_token:
            claims.update(jwt.decode(id_token, options={"verify_signature": False, "verify_aud": False}))
        access_token = tokens.get("access_token")
        if endpoints.get("userinfo") and access_token:
            info = await client.get(endpoints["userinfo"], headers={"Authorization": f"Bearer {access_token}"})
            if info.status_code < 400:
                payload = info.json()
                if isinstance(payload, dict):
                    claims.update(payload)
    user = user_from_claims(claims)
    logger.info("[OAUTH] signed in %s role=%s provider=%s", user.email, user.role.value, provider_name())
    return user

def frontend_redirect(token: Optional[str] = None, error: Optional[str] = None) -> str:
    base = (settings.oauth_frontend_redirect or "http://localhost:5173/auth/callback").rstrip("/")
    query = {}
    if token:
        query["access_token"] = token
    if error:
        query["error"] = error
    if not query:
        return base
    return f"{base}?{urlencode(query)}"
