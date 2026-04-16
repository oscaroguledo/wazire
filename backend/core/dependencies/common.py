from __future__ import annotations

from fastapi import Depends
from core.utils.token import TokenService
from core.config import get_settings
from core.middleware.auth import (
    require_lecturer,
    require_student,
    require_lecturer_or_admin,
    create_auth_dependency,
    require_admin,
    require_superadmin,
    require_admin_or_superadmin,
    require_student_or_above,
    require_lecturer_or_admin_or_superadmin,
)


def get_token_service() -> TokenService:
    """Get TokenService instance with secret from settings."""
    settings = get_settings()
    return TokenService(settings.SECRET_KEY.get_secret_value() if settings.SECRET_KEY else None)


# Get token service instance for auth functions
_token_service = get_token_service()

# Any authenticated user (all roles)
authenticated_dep = Depends(create_auth_dependency(_token_service))

# Single role dependencies
student_only_dep = Depends(require_student(_token_service))
lecturer_only_dep = Depends(require_lecturer(_token_service))
admin_only_dep = Depends(require_admin(_token_service))
superadmin_only_dep = Depends(require_superadmin(_token_service))

# Combined role dependencies
student_or_above_dep = Depends(require_student_or_above(_token_service))
lecturer_or_admin_dep = Depends(require_lecturer_or_admin(_token_service))
lecturer_or_admin_or_superadmin_dep = Depends(require_lecturer_or_admin_or_superadmin(_token_service))
admin_or_superadmin_dep = Depends(require_admin_or_superadmin(_token_service))