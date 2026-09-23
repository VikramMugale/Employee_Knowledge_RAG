"""Password hashing with bcrypt. SHA-256 is no longer used for credentials."""

from passlib.context import CryptContext

_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _context.hash(password or "")


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    try:
        return _context.verify(password or "", password_hash)
    except Exception:
        return False
