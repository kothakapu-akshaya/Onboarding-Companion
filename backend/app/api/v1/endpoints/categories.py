from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import col, func, select

from app.core.cache import cache_service
from app.core.rbac_fastapi import (
    get_user_roles,
    require_admin,
    require_any_role,
)
from app.db.session import SessionDep
from app.models.category import Category
from app.models.user import User
from app.schemas import CategoryRead as CategorySchema
from app.schemas import CategorySuggest

router = APIRouter()

CATEGORIES_CACHE_PREFIX = "categories"
CATEGORIES_CACHE_TTL = 300  # 5 minutes


def is_user_admin(user: User) -> bool:
    """Check if a user has admin role."""
    user_roles = get_user_roles(user.id)
    return "admin" in user_roles


@router.get("/", response_model=list[CategorySchema])
def get_categories(
    session: SessionDep, current_user: User = Depends(require_any_role())
) -> list[dict]:
    """Get all categories.

    Regular users see only approved categories, admins see all.
    """
    is_admin = is_user_admin(current_user)
    cache_key = "all" if is_admin else "approved"
    key = cache_service._build_key(CATEGORIES_CACHE_PREFIX, cache_key)

    def fetch():
        if is_admin:
            cats = session.exec(select(Category)).all()
        else:
            cats = session.exec(select(Category).where(Category.approved)).all()
        return [cat.model_dump(mode="json") for cat in cats]

    return cache_service.get_or_set(key, fetch, CATEGORIES_CACHE_TTL)


@router.get("/my-suggestions", response_model=list[CategorySchema])
def get_my_suggestions(
    session: SessionDep,
    current_user: User = Depends(require_any_role()),
) -> list[Category]:
    """Get all categories suggested by the current user."""
    categories = session.exec(
        select(Category).where(Category.suggested_by == current_user.id)
    ).all()
    return list(categories)


@router.get("/pending", response_model=list[CategorySchema])
def get_pending_categories(
    session: SessionDep,
    current_user: User = Depends(require_admin()),
) -> list[Category]:
    """Get all pending category suggestions that need admin approval."""
    categories = session.exec(
        select(Category).where(
            (col(Category.approved).is_(False))
            & (
                col(Category.suggested_by).isnot(None)
            )  # Only user-suggested categories
        )
    ).all()
    return list(categories)


@router.get("/{category_id}", response_model=CategorySchema)
def get_category(
    category_id: str,
    session: SessionDep,
    current_user: User = Depends(require_any_role()),
) -> dict:
    """Get a specific category by ID.

    Regular users can only see approved categories.
    """
    is_admin = is_user_admin(current_user)
    role = "admin" if is_admin else "user"
    key = cache_service._build_key(
        CATEGORIES_CACHE_PREFIX, "id", category_id, role
    )

    def fetch():
        category = session.get(Category, category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        if not is_admin and not category.approved:
            raise HTTPException(status_code=404, detail="Category not found")
        return category.model_dump(mode="json")

    return cache_service.get_or_set(key, fetch, CATEGORIES_CACHE_TTL)


@router.post("/", response_model=CategorySchema, status_code=201)
def create_category(
    category_data: Category,
    session: SessionDep,
    current_user: User = Depends(require_admin()),
) -> Category:
    """Create a new category (admin only).

    Admin-created categories are immediately approved.
    """
    # Normalize the category name for comparison
    # (strip whitespace and convert to lowercase)
    normalized_name = category_data.name.strip().lower()

    # Check if a category with the same name already exists (case-insensitive)
    existing = session.exec(
        select(Category).where(
            func.lower(func.trim(Category.name)) == normalized_name
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=400, detail="Category with this name already exists"
        )

    # Create new category - admin-created categories are immediately approved
    category = Category.model_validate(category_data.model_dump())
    category.approved = (
        True  # Admin-created categories are immediately approved
    )
    category.published = (
        True  # Admin-created categories are published by default
    )
    category.rank = 1  # Admin-created categories get rank of 1 by default
    category.approved_by = (
        current_user.id
    )  # Admin who created it is recorded as the approver
    session.add(category)
    session.commit()
    session.refresh(category)
    cache_service.invalidate(f"cache:{CATEGORIES_CACHE_PREFIX}:*")
    return category


@router.delete("/{category_id}")
def delete_category(
    category_id: str,
    session: SessionDep,
    current_user: User = Depends(require_admin()),
) -> dict:
    """Delete a category."""
    category = session.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    session.delete(category)
    session.commit()
    cache_service.invalidate(f"cache:{CATEGORIES_CACHE_PREFIX}:*")
    return {"message": "Category deleted successfully"}


# New endpoints for category suggestion workflow
@router.post("/suggest", response_model=CategorySchema, status_code=201)
def suggest_category(
    category_data: CategorySuggest,
    session: SessionDep,
    current_user: User = Depends(require_any_role()),
) -> Category:
    """Suggest a new category.

    The category will need admin approval before becoming public.
    """
    # Normalize the category name for comparison
    # (strip whitespace and convert to lowercase)
    normalized_name = category_data.name.strip().lower()

    # Check if a category with the same name already exists (approved or not)
    existing_category = session.exec(
        select(Category).where(
            func.lower(func.trim(Category.name)) == normalized_name
        )
    ).first()

    if existing_category:
        raise HTTPException(
            status_code=400, detail="A category with this name already exists"
        )

    # Check if user has already suggested a category with the same name
    # (for duplicate pending suggestions by same user)
    existing_suggestion = session.exec(
        select(Category).where(
            (func.lower(func.trim(Category.name)) == normalized_name)
            & (Category.suggested_by == current_user.id)
            & (~Category.approved)
        )
    ).first()

    if existing_suggestion:
        raise HTTPException(
            status_code=400,
            detail=(
                "You have already suggested a category with this name "
                "that is pending approval"
            ),
        )

    # Create new suggested category (not approved by default)
    category = Category.model_validate(category_data.model_dump())
    category.approved = False  # User-suggested categories start as not approved
    category.published = (
        False  # Initially not published (will be set on approval)
    )
    category.rank = 0  # Default rank (will be set on approval)
    category.suggested_by = current_user.id  # Record who suggested it
    # approved_by remains None until an admin approves it

    session.add(category)
    session.commit()
    session.refresh(category)
    cache_service.invalidate(f"cache:{CATEGORIES_CACHE_PREFIX}:*")
    return category


@router.put("/{category_id}/approve", response_model=CategorySchema)
def approve_category(
    category_id: str,
    session: SessionDep,
    current_user: User = Depends(require_admin()),
    publish: bool = Query(
        True, description="Whether to publish the category after approval"
    ),
) -> Category:
    """Approve a suggested category. Optionally publish it immediately."""
    category = session.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if category.approved:
        raise HTTPException(
            status_code=400, detail="Category is already approved"
        )

    # Approve the category
    category.approved = True
    category.approved_by = current_user.id

    # Optionally publish the category based on the parameter
    if publish:
        category.published = True  # Make it visible
        category.rank = 1  # Set rank to 1
    # If publish is False, only approval status changes,
    # visibility remains unchanged

    session.add(category)
    session.commit()
    session.refresh(category)
    cache_service.invalidate(f"cache:{CATEGORIES_CACHE_PREFIX}:*")
    return category


@router.put("/{category_id}/reject")
def reject_category(
    category_id: str,
    session: SessionDep,
    current_user: User = Depends(require_admin()),
) -> dict:
    """Reject a suggested category."""
    category = session.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if category.approved:
        raise HTTPException(
            status_code=400, detail="Cannot reject an already approved category"
        )

    # For now, we'll just delete the rejected category
    # Alternatively, we could add a 'rejected' field to keep track
    session.delete(category)
    session.commit()
    cache_service.invalidate(f"cache:{CATEGORIES_CACHE_PREFIX}:*")
    return {"message": "Category rejected successfully"}
