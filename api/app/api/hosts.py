from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, get_pagination_params, get_search_params
from app.models.user import User
from app.models.host import Host
from app.schemas.host import HostCreate, HostUpdate, HostResponse, HostConnectionTest
from app.schemas.common import PaginatedResponse

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[HostResponse])
async def list_hosts(
    pagination: dict = Depends(get_pagination_params),
    search: dict = Depends(get_search_params),
    group_id: Optional[str] = Query(None),
    is_favorite: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """List user's hosts."""
    hosts = await Host.get_user_hosts(
        db=db,
        user_id=str(current_user.id),
        group_id=group_id,
        is_favorite=is_favorite,
        search=search.get("query"),
        offset=pagination["offset"],
        limit=pagination["limit"]
    )

    total = await Host.get_user_hosts_count(
        db=db,
        user_id=str(current_user.id),
        group_id=group_id,
        is_favorite=is_favorite,
        search=search.get("query")
    )

    return PaginatedResponse.create(
        data=[HostResponse.from_orm(host) for host in hosts],
        total=total,
        page=pagination["page"],
        size=pagination["size"]
    )


@router.post("/", response_model=HostResponse)
async def create_host(
    host_data: HostCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Create a new host."""
    host = await Host.create(
        db=db,
        user_id=str(current_user.id),
        **host_data.dict()
    )
    return HostResponse.from_orm(host)


@router.get("/{host_id}", response_model=HostResponse)
async def get_host(
    host_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get host by ID."""
    host = await Host.get_by_id(db, host_id)
    if not host or host.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Host not found"
        )
    return HostResponse.from_orm(host)


@router.put("/{host_id}", response_model=HostResponse)
async def update_host(
    host_id: str,
    host_data: HostUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Update host."""
    host = await Host.get_by_id(db, host_id)
    if not host or host.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Host not found"
        )

    await host.update(db, **host_data.dict(exclude_unset=True))
    return HostResponse.from_orm(host)


@router.delete("/{host_id}")
async def delete_host(
    host_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Delete host."""
    host = await Host.get_by_id(db, host_id)
    if not host or host.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Host not found"
        )

    await host.delete(db)
    return {"message": "Host deleted successfully"}


@router.post("/{host_id}/test-connection", response_model=HostConnectionTest)
async def test_host_connection(
    host_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Test SSH connection to host."""
    host = await Host.get_by_id(db, host_id)
    if not host or host.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Host not found"
        )

    result = await host.test_connection(db)
    return HostConnectionTest(**result)


@router.post("/{host_id}/favorite")
async def toggle_favorite(
    host_id: str,
    is_favorite: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Toggle host favorite status."""
    host = await Host.get_by_id(db, host_id)
    if not host or host.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Host not found"
        )

    await host.set_favorite(db, is_favorite)
    return {"message": f"Host {'added to' if is_favorite else 'removed from'} favorites"}