# app/core/rbac_fastapi.py
"""Optimized FastAPI-compatible Role-Based Access Control (RBAC) System.

Simplified dependency injection with efficient caching and streamlined API
"""

from functools import lru_cache

from fastapi import Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.auth import get_current_active_user
from app.db.session import engine
from app.models.associations import UserRoleLink
from app.models.role import Role, RoleEnum
from app.models.user import User

# Permission matrix - centralized configuration using RoleEnum
PERMISSION_MATRIX: dict[RoleEnum, dict[str, set[str]]] = {
    RoleEnum.admin: {
        "users": {"GET", "POST", "PUT", "DELETE"},
        "records": {"GET", "POST", "PUT", "DELETE"},
        "categories": {"GET", "POST", "PUT", "DELETE"},
    },
    RoleEnum.reviewer: {
        "users": {"GET"},
        "records": {"GET", "PUT"},
        "categories": {"GET"},
    },
    RoleEnum.user: {
        "records": {"GET", "POST", "PUT"},
        "categories": {"GET"},
    },
}


# Utility functions for role management and permission checking


def clear_role_cache():
    """Clear the role cache - useful for testing or when roles change."""
    get_user_roles_cached.cache_clear()


def get_available_permissions(user_roles: list[str]) -> dict[str, set[str]]:
    """Get all available permissions for a user based on their roles.

    Returns:
        Dict mapping resource names to sets of allowed methods
    """
    permissions = {}
    user_roles_lower = {r.lower() for r in user_roles}

    for role_enum in PERMISSION_MATRIX:
        if role_enum.value in user_roles_lower:
            for resource, methods in PERMISSION_MATRIX[role_enum].items():
                if resource not in permissions:
                    permissions[resource] = set()
                permissions[resource].update(methods)

    return permissions


def can_user_access(user_id, resource: str, method: str) -> bool:
    """Check if a user can access a resource with a specific method.

    Useful for programmatic permission checks.
    """
    user_roles = get_user_roles(user_id)
    return has_permission(user_roles, resource, method)


def get_user_permission_summary(user_id) -> dict:
    """Get a summary of user's roles and permissions.

    Useful for debugging or user dashboards.
    """
    user_roles = get_user_roles(user_id)
    permissions = get_available_permissions(user_roles)

    return {
        "user_id": str(user_id),
        "roles": user_roles,
        "permissions": {
            resource: list(methods) for resource, methods in permissions.items()
        },
        "total_permissions": sum(
            len(methods) for methods in permissions.values()
        ),
    }


@lru_cache(maxsize=128)
def get_user_roles_cached(user_id: str) -> tuple:
    """Get role names for a user with caching to reduce database queries.

    Returns tuple for hashability in cache.
    """
    with Session(engine) as session:
        roles = session.exec(
            select(Role)
            .join(UserRoleLink)
            .where(UserRoleLink.user_id == user_id)
        ).all()

        role_names = []
        for role in roles:
            if hasattr(role.name, "value"):
                role_names.append(role.name.value)
            else:
                role_names.append(str(role.name))

        return tuple(role_names)


def get_user_roles(user_id) -> list[str]:
    """Get role names for a user."""
    return list(get_user_roles_cached(str(user_id)))


def has_permission(user_roles: list[str], resource: str, method: str) -> bool:
    """Check if any roles have permission for the resource and method."""
    resource_lower = resource.lower()
    method_upper = method.upper()
    user_roles_lower = {r.lower() for r in user_roles}

    for role_enum in PERMISSION_MATRIX:
        if role_enum.value in user_roles_lower:
            if resource_lower in PERMISSION_MATRIX[role_enum]:
                if method_upper in PERMISSION_MATRIX[role_enum][resource_lower]:
                    return True
    return False


def create_rbac_dependency(
    roles: RoleEnum | list[RoleEnum] | None = None,
    resource: str | None = None,
    method: str | None = None,
):
    """Unified dependency factory for RBAC checks.

    Args:
        roles: Required roles (RoleEnum or list of RoleEnums)
        resource: Resource name (e.g., "users", "records")
        method: HTTP method (e.g., "GET", "POST")
    """

    def check_access(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        if not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is inactive",
            )

        user_roles = get_user_roles(current_user.id)
        user_roles_lower = {r.lower() for r in user_roles}

        # If no restrictions specified, just require active user
        if not roles and not (resource and method):
            return current_user

        # Check role-based access
        if roles:
            if isinstance(roles, RoleEnum):
                allowed_roles = {roles.value}
            else:
                allowed_roles = {
                    (r.value if hasattr(r, "value") else r).lower()
                    for r in roles
                }

            if user_roles_lower.intersection(allowed_roles):
                return current_user

        # Check permission-based access
        if resource and method:
            if has_permission(user_roles, resource, method):
                return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Insufficient permissions.",
        )

    return check_access


# Simplified convenience functions
def require_admin():
    """Require admin role."""
    return create_rbac_dependency(roles=RoleEnum.admin)


def require_reviewer():
    """Require reviewer role (or admin)."""
    return create_rbac_dependency(roles=[RoleEnum.admin, RoleEnum.reviewer])


def require_any_role():
    """Require any authenticated user role."""
    return create_rbac_dependency(roles=list(RoleEnum))


def require_permission(resource: str, method: str):
    """Require specific permission."""
    return create_rbac_dependency(resource=resource, method=method)


# Advanced dependency functions


def require_any_permission(resource: str):
    """Require any permission on a resource (e.g. for read-only checks)."""

    def check_any_permission(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        if not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is inactive",
            )

        user_roles = get_user_roles(current_user.id)
        resource_lower = resource.lower()
        user_roles_lower = {r.lower() for r in user_roles}

        # Check if user has any permission on this resource
        for role_enum in PERMISSION_MATRIX:
            if role_enum.value in user_roles_lower:
                if resource_lower in PERMISSION_MATRIX[role_enum]:
                    return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. No permissions for resource: {resource}.",
        )

    return check_any_permission


def require_multiple_permissions(permissions: list[tuple]):
    """Require multiple permissions (ALL must be satisfied).

    Args:
        permissions: List of (resource, method) tuples
    """

    def check_multiple_permissions(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        if not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is inactive",
            )

        user_roles = get_user_roles(current_user.id)

        # Check each required permission
        missing_permissions = []
        for resource, method in permissions:
            if not has_permission(user_roles, resource, method):
                missing_permissions.append(f"{resource}:{method}")

        if missing_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access denied. Missing permissions: "
                    f"{missing_permissions}."
                ),
            )

        return current_user

    return check_multiple_permissions


# Resource-specific shortcuts (backwards compatibility)
def require_users_read():
    """Require permission to read users."""
    return require_permission("users", "GET")


def require_users_write():
    """Require permission to create users."""
    return require_permission("users", "POST")


def require_users_update():
    """Require permission to update users."""
    return require_permission("users", "PUT")


def require_users_delete():
    """Require permission to delete users."""
    return require_permission("users", "DELETE")


# Health check and system status functions


def get_rbac_system_status() -> dict:
    """Get the current status of the RBAC system.

    Useful for health checks and monitoring.
    """
    cache_info = get_user_roles_cached.cache_info()

    return {
        "system": "RBAC FastAPI",
        "version": "2.1-refactored",
        "status": "healthy",
        "features": {
            "role_caching": True,
            "permission_matrix": True,
            "unified_dependencies": True,
            "backwards_compatible": True,
        },
        "cache_stats": {
            "hits": cache_info.hits,
            "misses": cache_info.misses,
            "current_size": cache_info.currsize,
            "max_size": cache_info.maxsize,
            "hit_rate": cache_info.hits
            / max(cache_info.hits + cache_info.misses, 1),
        },
        "permission_matrix": {
            "total_roles": len(PERMISSION_MATRIX),
            "total_resources": len(
                set().union(
                    *[
                        resources.keys()
                        for resources in PERMISSION_MATRIX.values()
                    ]
                )
            ),
            "total_permissions": sum(
                len(methods)
                for role_perms in PERMISSION_MATRIX.values()
                for methods in role_perms.values()
            ),
        },
    }


def require_rbac_admin():
    """Special dependency for RBAC system administration.

    Only allows admin users to access RBAC management endpoints.
    """
    return create_rbac_dependency(roles=RoleEnum.admin)
