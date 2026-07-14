# Example RBAC monitoring endpoint
# Add this to your API router if you want system monitoring

from fastapi import APIRouter, Depends

from app.core.rbac_fastapi import get_rbac_system_status, require_rbac_admin
from app.models.user import User

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/rbac/status")
async def get_rbac_status(current_user: User = Depends(require_rbac_admin())):
    """Get RBAC system status and health information.

    Only accessible by admin users.
    """
    return get_rbac_system_status()


@router.post("/rbac/clear-cache")
async def clear_rbac_cache(current_user: User = Depends(require_rbac_admin())):
    """Clear the RBAC role cache.

    Useful for testing or when user roles are modified.
    Only accessible by admin users.
    """
    from app.core.rbac_fastapi import clear_role_cache

    # Get stats before clearing
    status_before = get_rbac_system_status()

    # Clear the cache
    clear_role_cache()

    # Get stats after clearing
    status_after = get_rbac_system_status()

    return {
        "message": "RBAC cache cleared successfully",
        "cache_before": status_before["cache_stats"],
        "cache_after": status_after["cache_stats"],
    }
