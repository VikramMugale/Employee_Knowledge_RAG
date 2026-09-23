"""OAuth 2.0 / OIDC authorization-code login with JWKS ID-token verification."""
from __future__ import annotations
from typing import Dict, Optional, Tuple
from urllib.parse import urlencode
import hmac
import secrets
import httpx
import jwt
from jwt import PyJWKClient
from backend.auth.authentication import AuthenticationError
from backend.auth.models import Role, User
from backend.auth.oauth_env import oauth_env
from backend.config.logging import logger

PROVIDERS = {
    "google": {
        "authorize": "https://accounts.google.com/o/oauth2/v2/auth",
        "token": "https://oauth2.googleapis.com/token",
        "userinfo": "https://openidconnect.googleapis.com/v1/userinfo",
        "discovery": "https://accounts.google.com/.well-known/openid-configuration",
        "issuer": "https://accounts.google.com",
        "jwks": "https://www.googleapis.com/oauth2/v3/certs",
        "scope": "openid email profile",
    },
    "microsoft": {
        "authorize": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
        "token": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
        "userinfo": "https://graph.microsoft.com/oidc/userinfo",
        "discovery": "https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration",
        "issuer": "https://login.microsoftonline.com/{tenant}/v2.0",
        "jwks": "https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys",
        "scope": "openid email profile User.Read",
    },
}
_jwks_clients: Dict[str, PyJWKClient] = {}

def provider_name() -> str:
    return (oauth_env.provider or "google").strip().lower()

def _tenant() -> str:
    return oauth_env.tenant or "common"

def _endpoints() -> Dict[str, str]:
    name = provider_name()
    tenant = _tenant()
    if name == "oidc":
        return {
            "authorize": oauth_env.authorize_url,
            "token": oauth_env.token_url,
            "userinfo": oauth_env.userinfo_url,
            "discovery": oauth_env.discovery_url,
            "issuer": oauth_env.issuer,
            "jwks": oauth_env.jwks_url,
            "scope": oauth_env.scope or "openid email profile",
        }
    preset = PROVIDERS.get(name)
    if not preset:
        raise AuthenticationError(f"Unsupported OAuth provider: {name}")
    return {key: (value.format(tenant=tenant) if isinstance(value, str) else value) for key, value in preset.items()}

def oauth_configured() -> bool:
    return bool(oauth_env.client_id and oauth_env.client_secret and oauth_env.redirect_uri)

def authorization_url() -> Tuple[str, str, str]:
    if not oauth_configured():
        raise AuthenticationError("OAuth is not configured.")
    endpoints = _endpoints()
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    params = {
        "client_id": oauth_env.client_id,
        "redirect_uri": oauth_env.redirect_uri,
        "response_type": "code",
        "scope": endpoints["scope"],
        "state": state,
        "nonce": nonce,
        "prompt": "select_account",
    }
    return f"{endpoints['authorize']}?{urlencode(params)}", state, nonce

def state_matches(cookie_state: Optional[str], query_state: Optional[str]) -> bool:
    if not cookie_state or not query_state:
        return False
    return hmac.compare_digest(cookie_state, query_state)

def _jwks_client(url: str) -> PyJWKClient:
    if url not in _jwks_clients:
        _jwks_clients[url] = PyJWKClient(url, cache_jwk_set=True, lifespan=3600)
    return _jwks_clients[url]

async def _resolve_jwks_and_issuer(client: httpx.AsyncClient, endpoints: Dict[str, str]) -> Tuple[str, str]:
    jwks = endpoints.get("jwks") or ""
    issuer = endpoints.get("issuer") or ""
    discovery = endpoints.get("discovery") or ""
    if discovery:
        try:
            response = await client.get(discovery)
            if response.status_code < 400:
                meta = response.json()
                jwks = meta.get("jwks_uri") or jwks
                issuer = meta.get("issuer") or issuer
        except Exception as exc:
            logger.warning("[OAUTH] discovery failed: %s", exc)
    if not jwks or not issuer:
        raise AuthenticationError("OIDC JWKS/issuer missing; cannot verify the ID token.")
    return jwks, issuer

def _expected_issuers(issuer: str) -> list:
    values = [issuer]
    tenant = _tenant()
    if provider_name() == "microsoft" and tenant not in {"common", "organizations", "consumers"}:
        values.append(f"https://login.microsoftonline.com/{tenant}/v2.0")
    return values

def verify_id_token(id_token: str, jwks_url: str, issuer: str, nonce: str) -> Dict:
    try:
        signing_key = _jwks_client(jwks_url).get_signing_key_from_jwt(id_token)
        claims = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256", "RS384", "RS512"],
            audience=oauth_env.client_id,
            issuer=_expected_issuers(issuer),
            options={"require": ["exp", "iat", "iss", "aud"], "verify_aud": True, "verify_iss": True, "verify_exp": True},
            leeway=30,
        )
    except jwt.PyJWTError as exc:
        logger.warning("[OAUTH] ID token verification failed: %s", exc)
        raise AuthenticationError("Invalid identity token.") from exc
    token_nonce = claims.get("nonce")
    if not nonce or not token_nonce or not hmac.compare_digest(str(token_nonce), nonce):
        raise AuthenticationError("OIDC nonce mismatch.")
    if provider_name() == "microsoft":
        tid = str(claims.get("tid") or "")
        tenant = _tenant()
        if tenant not in {"common", "organizations", "consumers"} and tid and tid.lower() != tenant.lower():
            raise AuthenticationError("Microsoft tenant mismatch.")
    return claims

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

async def exchange_code(code: str, nonce: str) -> User:
    endpoints = _endpoints()
    data = {"client_id": oauth_env.client_id, "client_secret": oauth_env.client_secret, "code": code, "grant_type": "authorization_code", "redirect_uri": oauth_env.redirect_uri}
    async with httpx.AsyncClient(timeout=20.0) as client:
        token_response = await client.post(endpoints["token"], data=data, headers={"Accept": "application/json"})
        if token_response.status_code >= 400:
            raise AuthenticationError("OAuth token exchange failed.")
        tokens = token_response.json()
        id_token = tokens.get("id_token")
        if not id_token:
            raise AuthenticationError("Provider did not return an ID token.")
        jwks_url, issuer = await _resolve_jwks_and_issuer(client, endpoints)
        claims = verify_id_token(id_token, jwks_url, issuer, nonce)
        if endpoints.get("userinfo") and tokens.get("access_token"):
            info = await client.get(endpoints["userinfo"], headers={"Authorization": f"Bearer {tokens['access_token']}"})
            if info.status_code < 400 and isinstance(info.json(), dict):
                extra = info.json()
                for key in ("email", "name", "preferred_username"):
                    if extra.get(key) and not claims.get(key):
                        claims[key] = extra[key]
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
    return f"{base}?{urlencode(query)}" if query else base
