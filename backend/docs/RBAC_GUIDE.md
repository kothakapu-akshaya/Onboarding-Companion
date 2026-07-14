# RBAC System Usage Guide

## Optimized FastAPI RBAC System

The optimized RBAC system provides a unified, efficient way to handle role-based and permission-based access control in FastAPI applications.

### Key Improvements

1. **🚀 Performance**: 
   - Uses `@lru_cache` for role lookups to reduce database queries
   - Single unified dependency factory instead of multiple similar functions
   - Centralized permission matrix for easy maintenance

2. **🎯 Simplicity**:
   - One main function `create_rbac_dependency()` handles all scenarios
   - Cleaner API with fewer functions to remember
   - Backwards compatibility with existing specific functions

3. **🔧 Maintainability**:
   - Permission matrix defined in one place (`PERMISSION_MATRIX`)
   - Easy to add new roles or modify permissions
   - Clear separation of concerns

### Usage Examples

#### 1. Role-Based Access Control

```python
from app.core.rbac_fastapi import create_rbac_dependency, require_admin

# Require admin role only
@router.get("/admin-only")
async def admin_endpoint(
    current_user: User = Depends(require_admin())
):
    return {"message": "Admin access"}

# Require admin OR reviewer role
@router.get("/moderator-access")
async def moderator_endpoint(
    current_user: User = Depends(create_rbac_dependency(roles=["admin", "reviewer"]))
):
    return {"message": "Moderator access"}
```

#### 2. Permission-Based Access Control

```python
from app.core.rbac_fastapi import create_rbac_dependency, require_permission

# Require specific permission
@router.get("/records")
async def get_records(
    current_user: User = Depends(require_permission("records", "GET"))
):
    return records

# Using the unified factory
@router.put("/records/{record_id}")
async def update_record(
    record_id: str,
    current_user: User = Depends(create_rbac_dependency(resource="records", method="PUT"))
):
    return {"updated": record_id}
```

#### 3. Backwards Compatibility

```python
from app.core.rbac_fastapi import require_users_read, require_users_write

# These still work exactly as before
@router.get("/users/")
async def get_users(
    current_user: User = Depends(require_users_read())
):
    return users

@router.post("/users/")
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_users_write())
):
    return new_user
```

### Permission Matrix

The system uses a centralized permission matrix:

```python
PERMISSION_MATRIX = {
    "admin": {
        "users": {"GET", "POST", "PUT", "DELETE"},
        "records": {"GET", "POST", "PUT", "DELETE"},
        "categories": {"GET", "POST", "PUT", "DELETE"},
    },
    "reviewer": {
        "users": {"GET"},
        "records": {"GET", "PUT"},
        "categories": {"GET"},
    },
    "user": {
        "records": {"GET"},
        "categories": {"GET"},
    }
}
```

### Adding New Resources/Permissions

To add a new resource (e.g., "reports"):

1. Update `PERMISSION_MATRIX` in `app/core/rbac_fastapi.py`:
```python
PERMISSION_MATRIX = {
    "admin": {
        # ... existing permissions ...
        "reports": {"GET", "POST", "PUT", "DELETE"},
    },
    "reviewer": {
        # ... existing permissions ...
        "reports": {"GET"},
    },
    # ... etc
}
```

2. Use in your endpoints:
```python
@router.get("/reports")
async def get_reports(
    current_user: User = Depends(require_permission("reports", "GET"))
):
    return reports
```

### Performance Benefits

- **Database Query Reduction**: Role lookups are cached, reducing database hits
- **Single Code Path**: One unified dependency function instead of many specialized ones
- **Efficient Permission Checks**: Fast dictionary/set lookups instead of complex logic

### Migration from Old System

The new system is fully backwards compatible. You can:

1. Keep using existing functions like `require_admin()`, `require_users_read()`, etc.
2. Gradually migrate to the unified `create_rbac_dependency()` approach
3. Or use a mix of both approaches

### Testing

The system includes comprehensive tests to verify:
- ✅ Unauthenticated access is blocked
- ✅ Authentication works correctly
- ✅ Role-based permissions work
- ✅ Permission-based access control works
- ✅ Caching improves performance
- ✅ Error messages are informative

### Common Patterns

```python
# Just require any authenticated user
current_user: User = Depends(create_rbac_dependency())

# Require specific role
current_user: User = Depends(create_rbac_dependency(roles="admin"))

# Require one of multiple roles
current_user: User = Depends(create_rbac_dependency(roles=["admin", "reviewer"]))

# Require specific permission
current_user: User = Depends(create_rbac_dependency(resource="users", method="GET"))

# Use convenience functions
current_user: User = Depends(require_admin())
current_user: User = Depends(require_permission("records", "PUT"))
```
