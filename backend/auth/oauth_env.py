import os
from backend.config.settings import settings

def _get(name: str, default: str = "") -> str:
    mapping = {
        "oauth_provider": "OAUTH_PROVIDER",
        "oauth_client_id": "OAUTH_CLIENT_ID",
        "oauth_client_secret": "OAUTH_CLIENT_SECRET",
        "oauth_redirect_uri": "OAUTH_REDIRECT_URI",
        "oauth_frontend_redirect": "OAUTH_FRONTEND_REDIRECT",
        "oauth_tenant": "OAUTH_TENANT",
        "oauth_scope": "OAUTH_SCOPE",
        "oauth_authorize_url": "OAUTH_AUTHORIZE_URL",
        "oauth_token_url": "OAUTH_TOKEN_URL",
        "oauth_userinfo_url": "OAUTH_USERINFO_URL",
        "oauth_admin_emails": "OAUTH_ADMIN_EMAILS",
        "oauth_discovery_url": "OAUTH_DISCOVERY_URL",
        "oauth_issuer": "OAUTH_ISSUER",
        "oauth_jwks_url": "OAUTH_JWKS_URL",
        "oidc_issuer": "OIDC_ISSUER",
        "oidc_jwks_url": "OIDC_JWKS_URL",
    }
    return getattr(settings, name, None) or os.getenv(mapping.get(name, name.upper()), default) or default

class OAuthEnv:
    provider = property(lambda self: _get("oauth_provider", "google"))
    client_id = property(lambda self: _get("oauth_client_id"))
    client_secret = property(lambda self: _get("oauth_client_secret"))
    redirect_uri = property(lambda self: _get("oauth_redirect_uri", "http://localhost:8000/api/v1/auth/oauth/callback"))
    frontend_redirect = property(lambda self: _get("oauth_frontend_redirect", "http://localhost:5173/auth/callback"))
    tenant = property(lambda self: _get("oauth_tenant", "common"))
    scope = property(lambda self: _get("oauth_scope"))
    authorize_url = property(lambda self: _get("oauth_authorize_url"))
    token_url = property(lambda self: _get("oauth_token_url"))
    userinfo_url = property(lambda self: _get("oauth_userinfo_url"))
    admin_emails = property(lambda self: _get("oauth_admin_emails"))
    discovery_url = property(lambda self: _get("oauth_discovery_url"))
    issuer = property(lambda self: _get("oauth_issuer") or _get("oidc_issuer"))
    jwks_url = property(lambda self: _get("oauth_jwks_url") or _get("oidc_jwks_url"))

oauth_env = OAuthEnv()
