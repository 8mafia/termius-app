from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_admin_user
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.schemas.common import PaginatedResponse, PaginationParams

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[UserResponse])
async def list_users(
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """List all users (admin only)."""
    # TODO: Implement user listing with pagination
    return PaginatedResponse.create(
        data=[UserResponse.from_orm(current_user)],
        total=1,
        page=pagination.page,
        size=pagination.size
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get user by ID (admin only)."""
    # TODO: Implement user retrieval
    return UserResponse.from_orm(current_user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Update user (admin only)."""
    # TODO: Implement user update
    return UserResponse.from_orm(current_user)


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Delete user (admin only)."""
    # TODO: Implement user deletion
    return {"message": "User deleted successfully"}