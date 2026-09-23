"""OAuth 2.0 authorization-code login for Google, Microsoft Entra ID, or generic OIDC."""
from __future__ import annotations
from typing import Dict, Optional, Tuple
from urllib.parse import urlencode
import secrets
import httpx
import jwt
from backend.auth.authentication import AuthenticationError
from backend.auth.models import Role, User
from backend.auth.oauth_env import oauth_env
from backend.config.logging import logger

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
    return (oauth_env.provider or "google").strip().lower()

def _endpoints() -> Dict[str, str]:
    name = provider_name()
    tenant = oauth_env.tenant or "common"
    if name == "oidc":
        return {"authorize": oauth_env.authorize_url, "token": oauth_env.token_url, "userinfo": oauth_env.userinfo_url, "scope": oauth_env.scope or "openid email profile"}
    preset = PROVIDERS.get(name)
    if not preset:
        raise AuthenticationError(f"Unsupported OAuth provider: {name}")
    return {
        "authorize": preset["authorize"].format(tenant=tenant),
        "token": preset["token"].format(tenant=tenant),
        "userinfo": preset["userinfo"],
        "scope": oauth_env.scope or preset["scope"],
    }

def oauth_configured() -> bool:
    return bool(oauth_env.client_id and oauth_env.client_secret and oauth_env.redirect_uri)

def authorization_url() -> Tuple[str, str]:
    if not oauth_configured():
        raise AuthenticationError("OAuth is not configured. Set OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET, and OAUTH_REDIRECT_URI.")
    endpoints = _endpoints()
    state = secrets.token_urlsafe(24)
    params = {"client_id": oauth_env.client_id, "redirect_uri": oauth_env.redirect_uri, "response_type": "code", "scope": endpoints["scope"], "state": state, "prompt": "select_account"}
    return f"{endpoints['authorize']}?{urlencode(params)}", state

def user_from_claims(claims: Dict) -> User:
    email = (claims.get("email") or claims.get("preferred_username") or claims.get("upn") or "").strip()
    if not email:
        raise AuthenticationError("OAuth provider did not return an email address.")
    admins = {item.strip().lower() for item in (oauth_env.admin_emails or "").split(",") if item.strip()}
    groups = claims.get("groups") or claims.get("roles") or []
    if isinstance(groups, str):
        groups = [groups]
    role = Role.ADMIN if email.lower() in admins or "admin" in " ".join(str(item).lower() for item in groups) else Role.EMPLOYEE
    subject = str(claims.get("sub") or claims.get("oid") or email)
    return User(id=f"oauth_{subject}"[:64], email=email, full_name=str(claims.get("name") or email.split("@")[0]), role=role)

async def exchange_code(code: str) -> User:
    endpoints = _endpoints()
    data = {"client_id": oauth_env.client_id, "client_secret": oauth_env.client_secret, "code": code, "grant_type": "authorization_code", "redirect_uri": oauth_env.redirect_uri}
    async with httpx.AsyncClient(timeout=20.0) as client:
        token_response = await client.post(endpoints["token"], data=data, headers={"Accept": "application/json"})
        if token_response.status_code >= 400:
            logger.warning("[OAUTH] token exchange failed: %s %s", token_response.status_code, token_response.text[:300])
            raise AuthenticationError("OAuth token exchange failed.")
        tokens = token_response.json()
        claims: Dict = {}
        if tokens.get("id_token"):
            claims.update(jwt.decode(tokens["id_token"], options={"verify_signature": False, "verify_aud": False}))
        if endpoints.get("userinfo") and tokens.get("access_token"):
            info = await client.get(endpoints["userinfo"], headers={"Authorization": f"Bearer {tokens['access_token']}"})
            if info.status_code < 400 and isinstance(info.json(), dict):
                claims.update(info.json())
    user = user_from_claims(claims)
    logger.info("[OAUTH] signed in %s role=%s provider=%s", user.email, user.role.value, provider_name())
    return user

def frontend_redirect(token: Optional[str] = None, error: Optional[str] = None) -> str:
    base = (oauth_env.frontend_redirect or "http://localhost:5173/auth/callback").rstrip("/")
    query = {}
    if token:
        query["access_token"] = token
    if error:
        query["error"] = error
    from urllib.parse import urlencode as enc
    return f"{base}?{enc(query)}" if query else base
