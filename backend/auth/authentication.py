"""
Local JWT authentication using PyJWT (HS256). No Microsoft SSO / OIDC.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
import hashlib
import hmac
import jwt
from backend.auth.models import User, UserContext, Role
from backend.config.logging import logger
from backend.config.settings import settings


ROLE_ACCESS = {
    Role.ADMIN: ["PUBLIC_INTERNAL", "INTERNAL_RESTRICTED"],
    Role.EMPLOYEE: ["PUBLIC_INTERNAL"],
}


class AuthenticationError(Exception):
    """Raised when a bearer token cannot be authenticated."""


def _hash_password(password: str) -> str:
    return hashlib.sha256(f"{settings.secret_key}:{password}".encode("utf-8")).hexdigest()


def _build_user(
    user_id: str,
    email: str,
    full_name: str,
    role: Role,
    department: str,
    password: str,
) -> Dict:
    return {
        "user": User(
            id=user_id,
            email=email,
            full_name=full_name,
            role=role,
            department=department,
            location="Global",
            employment_type="full_time",
        ),
        "password_hash": _hash_password(password),
    }


SEED_USERS: Dict[str, Dict] = {
    "employee@acme.com": _build_user(
        "user_emp_01", "employee@acme.com", "Alex Employee", Role.EMPLOYEE, "General", "employee123"
    ),
    "admin@acme.com": _build_user(
        "user_admin_01", "admin@acme.com", "Avery Admin", Role.ADMIN, "IT", "admin123"
    ),
}


class AuthenticationService:
    """Issues and verifies locally signed JWTs with PyJWT."""

    def authenticate_credentials(self, email: str, password: str) -> User:
        record = SEED_USERS.get((email or "").strip().lower())
        if not record:
            raise AuthenticationError("Invalid email or password.")
        incoming = _hash_password(password or "")
        if not hmac.compare_digest(incoming, record["password_hash"]):
            raise AuthenticationError("Invalid email or password.")
        return record["user"]

    def issue_token(self, user: User) -> str:
        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=settings.jwt_expire_minutes)
        payload = {
            "sub": user.id,
            "email": user.email,
            "name": user.full_name,
            "role": user.role.value,
            "department": user.department,
            "location": user.location,
            "employment_type": user.employment_type,
            "access_levels": ROLE_ACCESS.get(user.role, ["PUBLIC_INTERNAL"]),
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": int(now.timestamp()),
            "exp": int(expires.timestamp()),
        }
        return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    def authenticate_token(self, token: str) -> UserContext:
        raw = (token or "").strip()
        if not raw:
            raise AuthenticationError("Empty authorization token.")
        if raw.lower().startswith("bearer "):
            raw = raw[7:].strip()

        try:
            payload = jwt.decode(
                raw,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
                audience=settings.jwt_audience,
                issuer=settings.jwt_issuer,
            )
        except jwt.ExpiredSignatureError as exc:
            raise AuthenticationError("Token has expired.") from exc
        except jwt.InvalidTokenError as exc:
            logger.warning("[AUTH] JWT verification failed: %s", exc)
            raise AuthenticationError("Invalid or unsupported authorization token.") from exc

        role = self._parse_role(payload.get("role"))
        return UserContext(
            user_id=str(payload.get("sub") or "unknown"),
            email=payload.get("email"),
            full_name=payload.get("name"),
            role=role,
            department=str(payload.get("department") or "General"),
            location=str(payload.get("location") or "Global"),
            employment_type=str(payload.get("employment_type") or "full_time"),
            allowed_access_levels=list(payload.get("access_levels") or ROLE_ACCESS.get(role, ["PUBLIC_INTERNAL"])),
        )

    def user_from_context(self, context: UserContext) -> User:
        email = (context.email or "").lower()
        if email in SEED_USERS:
            return SEED_USERS[email]["user"]
        return User(
            id=context.user_id,
            email=context.email or f"{context.user_id}@acme.com",
            full_name=context.full_name or context.user_id,
            role=context.role,
            department=context.department,
            location=context.location,
            employment_type=context.employment_type,
        )

    def _parse_role(self, raw_role) -> Role:
        if isinstance(raw_role, list) and raw_role:
            raw_role = raw_role[0]
        if not raw_role:
            return Role.EMPLOYEE
        try:
            return Role(str(raw_role).upper())
        except ValueError:
            return Role.EMPLOYEE


auth_service = AuthenticationService()
