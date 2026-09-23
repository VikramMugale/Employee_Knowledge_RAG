"""
Authentication and authorization domain models for RBAC and ABAC.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class Role(str, Enum):
    """System roles. Keep this to two until document ACLs actually need more."""
    EMPLOYEE = "EMPLOYEE"
    ADMIN = "ADMIN"


class Permission(str, Enum):
    """Actions the two roles can take."""
    READ_PUBLIC_POLICY = "read:public_policy"
    MANAGE_DOCUMENTS = "manage:documents"
    VIEW_ANALYTICS = "view:analytics"
    ADMIN_ALL = "admin:all"


class User(BaseModel):
    """User identity domain model."""
    id: str
    email: str
    full_name: str
    role: Role = Role.EMPLOYEE
    department: str = "General"
    location: str = "Global"
    employment_type: str = "full_time"
    permissions: List[Permission] = Field(default_factory=list)


class UserContext(BaseModel):
    """User context for generating database-level ACL metadata filters."""
    user_id: str
    role: Role
    department: str
    location: str
    employment_type: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    allowed_access_levels: List[str] = Field(default_factory=lambda: ["PUBLIC_INTERNAL"])


class LoginRequest(BaseModel):
    """Email/password login payload."""
    email: str
    password: str


class TokenResponse(BaseModel):
    """Signed JWT session response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: User


class UserProfile(BaseModel):
    """Public profile returned by /auth/me."""
    id: str
    email: str
    full_name: str
    role: Role
    department: str
    location: str
    employment_type: str
    allowed_access_levels: List[str]
