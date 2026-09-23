"""
Authorization engine for the two-role model.
"""

from backend.auth.models import UserContext, Role, Permission


class AuthorizationEngine:
    """Employees can read public policy. Admins can do everything else."""

    def authorize_access(self, user_context: UserContext, required_permission: Permission) -> bool:
        if user_context.role == Role.ADMIN:
            return True
        if required_permission == Permission.READ_PUBLIC_POLICY:
            return user_context.role == Role.EMPLOYEE
        return False


authorization_engine = AuthorizationEngine()
