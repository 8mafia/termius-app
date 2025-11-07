from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.group import Group
from app.schemas.group import GroupCreate, GroupUpdate, GroupResponse
from app.schemas.common import SuccessResponse

router = APIRouter()


@router.get("/", response_model=List[GroupResponse])
async def list_groups(
    parent_group_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """List user's groups."""
    groups = await Group.get_user_groups(
        db=db,
        user_id=str(current_user.id),
        parent_group_id=parent_group_id
    )
    return [GroupResponse.from_orm(group) for group in groups]


@router.post("/", response_model=GroupResponse)
async def create_group(
    group_data: GroupCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Create a new group."""
    group = await Group.create(
        db=db,
        user_id=str(current_user.id),
        **group_data.dict()
    )
    return GroupResponse.from_orm(group)


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get group by ID."""
    group = await Group.get_by_id(db, group_id)
    if not group or group.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    return GroupResponse.from_orm(group)


@router.put("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: str,
    group_data: GroupUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Update group."""
    group = await Group.get_by_id(db, group_id)
    if not group or group.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )

    await group.update(db, **group_data.dict(exclude_unset=True))
    return GroupResponse.from_orm(group)


@router.delete("/{group_id}")
async def delete_group(
    group_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Delete group."""
    group = await Group.get_by_id(db, group_id)
    if not group or group.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )

    await group.delete(db)
    return {"message": "Group deleted successfully"}