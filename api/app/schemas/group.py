from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class GroupBase(BaseModel):
    """Base group schema."""
    name: str = Field(..., description="Group name")
    description: Optional[str] = Field(None, description="Group description")
    color: Optional[str] = Field(None, description="Display color")
    icon: Optional[str] = Field(None, description="Icon name")


class GroupCreate(GroupBase):
    """Group creation schema."""
    parent_group_id: Optional[str] = Field(None, description="Parent group ID")


class GroupUpdate(BaseModel):
    """Group update schema."""
    name: Optional[str] = Field(None, description="Group name")
    description: Optional[str] = Field(None, description="Group description")
    color: Optional[str] = Field(None, description="Display color")
    icon: Optional[str] = Field(None, description="Icon name")
    parent_group_id: Optional[str] = Field(None, description="Parent group ID")


class GroupResponse(GroupBase):
    """Group response schema."""
    id: str = Field(..., description="Group ID")
    user_id: str = Field(..., description="User ID")
    parent_group_id: Optional[str] = Field(None, description="Parent group ID")
    settings: Dict[str, Any] = Field(default_factory=dict, description="Group settings")
    is_default: bool = Field(default=False, description="Is default group")
    created_at: Optional[str] = Field(None, description="Creation time")
    updated_at: Optional[str] = Field(None, description="Last update time")
    is_active: bool = Field(default=True, description="Is active")
    sort_order: int = Field(default=0, description="Sort order")

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj):
        """Create from ORM object."""
        return cls(
            id=str(obj.id),
            user_id=str(obj.user_id),
            parent_group_id=str(obj.parent_group_id) if obj.parent_group_id else None,
            name=obj.name,
            description=obj.description,
            color=obj.color,
            icon=obj.icon,
            settings=obj.settings or {},
            is_default=obj.is_default,
            created_at=obj.created_at.isoformat() if obj.created_at else None,
            updated_at=obj.updated_at.isoformat() if obj.updated_at else None,
            is_active=obj.is_active,
            sort_order=obj.sort_order
        )


class GroupHierarchy(BaseModel):
    """Group hierarchy structure."""
    group: GroupResponse = Field(..., description="Group info")
    children: List["GroupHierarchy"] = Field(default_factory=list, description="Child groups")
    hosts_count: int = Field(default=0, description="Number of hosts in this group and subgroups")


# Forward reference for recursive type
GroupHierarchy.model_rebuild()