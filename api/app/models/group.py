import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, String, Boolean, DateTime, JSON,
    Index, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update, delete, text

from app.core.database import Base


class Group(Base):
    """Group model for organizing hosts."""

    __tablename__ = "groups"

    # Primary fields
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    parent_group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=True)

    # Group details
    name = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    color = Column(String(7), nullable=True)  # Hex color code
    icon = Column(String(50), nullable=True)  # Icon name

    # Settings
    settings = Column(JSON, default=dict, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)

    # Relationships
    user = relationship("User", back_populates="groups")
    parent_group = relationship("Group", remote_side=[id], backref="child_groups")
    hosts = relationship("Host", back_populates="group", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_groups_user_id', 'user_id'),
        Index('idx_groups_parent_id', 'parent_group_id'),
        Index('idx_groups_name', 'name'),
        Index('idx_groups_active', 'is_active'),
        Index('idx_groups_sort', 'sort_order'),
        Index('idx_groups_created', 'created_at'),
    )

    def __repr__(self):
        return f"<Group(id={self.id}, name={self.name}, user_id={self.user_id})>"

    @classmethod
    async def create(
        cls,
        db: AsyncSession,
        user_id: str,
        name: str,
        parent_group_id: Optional[str] = None,
        **kwargs
    ) -> "Group":
        """Create a new group."""
        group = cls(
            user_id=user_id,
            name=name,
            parent_group_id=parent_group_id,
            **kwargs
        )

        db.add(group)
        await db.commit()
        await db.refresh(group)
        return group

    @classmethod
    async def get_by_id(cls, db: AsyncSession, group_id: str) -> Optional["Group"]:
        """Get group by ID."""
        result = await db.execute(
            select(cls).where(cls.id == group_id)
        )
        return result.scalar_one_or_none()

    @classmethod
    async def get_user_groups(
        cls,
        db: AsyncSession,
        user_id: str,
        parent_group_id: Optional[str] = None,
        include_inactive: bool = False
    ) -> List["Group"]:
        """Get user's groups."""
        query = select(cls).where(cls.user_id == user_id)

        if parent_group_id:
            query = query.where(cls.parent_group_id == parent_group_id)
        else:
            # Get root groups (no parent)
            query = query.where(cls.parent_group_id.is_(None))

        if not include_inactive:
            query = query.where(cls.is_active == True)

        query = query.order_by(cls.sort_order.asc(), cls.name.asc())

        result = await db.execute(query)
        return result.scalars().all()

    @classmethod
    async def get_default_group(cls, db: AsyncSession, user_id: str) -> Optional["Group"]:
        """Get user's default group."""
        result = await db.execute(
            select(cls)
            .where(
                and_(
                    cls.user_id == user_id,
                    cls.is_default == True,
                    cls.is_active == True
                )
            )
        )
        return result.scalar_one_or_none()

    @classmethod
    async def create_default_group(cls, db: AsyncSession, user_id: str) -> "Group":
        """Create default group for user."""
        # Check if default group already exists
        existing = await cls.get_default_group(db, user_id)
        if existing:
            return existing

        group = cls(
            user_id=user_id,
            name="Default",
            description="Default group for hosts",
            is_default=True,
            color="#6366f1"
        )

        db.add(group)
        await db.commit()
        await db.refresh(group)
        return group

    @classmethod
    async def get_group_hierarchy(
        cls,
        db: AsyncSession,
        user_id: str,
        group_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get group hierarchy as nested structure."""
        # This is a complex query that builds the full hierarchy
        # For now, we'll implement a simple version

        if group_id:
            root_group = await cls.get_by_id(db, group_id)
            if not root_group or root_group.user_id != user_id:
                return []
        else:
            # Get root groups
            root_groups = await cls.get_user_groups(db, user_id)
            hierarchy = []
            for group in root_groups:
                children = await cls.get_group_children(db, group.id)
                hierarchy.append({
                    "group": group,
                    "children": children
                })
            return hierarchy

        return []

    @classmethod
    async def get_group_children(
        cls,
        db: AsyncSession,
        parent_group_id: str
    ) -> List[Dict[str, Any]]:
        """Get child groups of a group."""
        result = await db.execute(
            select(cls)
            .where(
                and_(
                    cls.parent_group_id == parent_group_id,
                    cls.is_active == True
                )
            )
            .order_by(cls.sort_order.asc(), cls.name.asc())
        )
        children = result.scalars().all()

        hierarchy = []
        for child in children:
            child_children = await cls.get_group_children(db, child.id)
            hierarchy.append({
                "group": child,
                "children": child_children
            })

        return hierarchy

    @classmethod
    async def get_all_user_groups_flat(
        cls,
        db: AsyncSession,
        user_id: str
    ) -> List["Group"]:
        """Get all user groups as flat list."""
        result = await db.execute(
            select(cls)
            .where(
                and_(
                    cls.user_id == user_id,
                    cls.is_active == True
                )
            )
            .order_by(cls.name.asc())
        )
        return result.scalars().all()

    @classmethod
    async def search_groups(
        cls,
        db: AsyncSession,
        user_id: str,
        search_term: str
    ) -> List["Group"]:
        """Search groups by name or description."""
        search_pattern = f"%{search_term}%"
        result = await db.execute(
            select(cls)
            .where(
                and_(
                    cls.user_id == user_id,
                    cls.is_active == True,
                    or_(
                        cls.name.ilike(search_pattern),
                        cls.description.ilike(search_pattern)
                    )
                )
            )
            .order_by(cls.name.asc())
        )
        return result.scalars().all()

    async def update(self, db: AsyncSession, **kwargs) -> None:
        """Update group details."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.utcnow()
        await db.commit()

    async def move_to_parent(
        self,
        db: AsyncSession,
        new_parent_id: Optional[str] = None
    ) -> None:
        """Move group to new parent."""
        # Check for circular reference
        if new_parent_id and await self._would_create_circular_reference(db, new_parent_id):
            raise ValueError("Cannot move group: would create circular reference")

        self.parent_group_id = new_parent_id
        self.updated_at = datetime.utcnow()
        await db.commit()

    async def _would_create_circular_reference(
        self,
        db: AsyncSession,
        new_parent_id: str
    ) -> bool:
        """Check if moving group would create circular reference."""
        # Simple implementation: check if new_parent is a descendant of this group
        descendants = await self.get_all_descendants(db)
        descendant_ids = [str(d.id) for d in descendants]
        return new_parent_id in descendant_ids

    async def get_all_descendants(self, db: AsyncSession) -> List["Group"]:
        """Get all descendant groups."""
        result = await db.execute(
            text("""
                WITH RECURSIVE group_descendants AS (
                    SELECT id, name, parent_group_id, user_id
                    FROM groups
                    WHERE parent_group_id = :group_id

                    UNION ALL

                    SELECT g.id, g.name, g.parent_group_id, g.user_id
                    FROM groups g
                    INNER JOIN group_descendants gd ON g.parent_group_id = gd.id
                )
                SELECT * FROM groups WHERE id IN (SELECT id FROM group_descendants) AND is_active = true
                ORDER BY name
            """),
            {"group_id": str(self.id)}
        )
        return result.scalars().all()

    async def get_hosts_count(self, db: AsyncSession) -> int:
        """Get count of hosts in this group (including subgroups)."""
        from .host import Host

        # Get all descendant groups
        descendant_ids = [str(self.id)]
        descendants = await self.get_all_descendants(db)
        descendant_ids.extend([str(d.id) for d in descendants])

        result = await db.execute(
            select(func.count(Host.id))
            .where(
                and_(
                    Host.group_id.in_(descendant_ids),
                    Host.is_active == True
                )
            )
        )
        return result.scalar() or 0

    async def set_sort_order(self, db: AsyncSession, sort_order: int) -> None:
        """Set sort order."""
        self.sort_order = sort_order
        self.updated_at = datetime.utcnow()
        await db.commit()

    async def soft_delete(self, db: AsyncSession) -> None:
        """Soft delete group."""
        # Check if group has hosts
        hosts_count = await self.get_hosts_count(db)
        if hosts_count > 0:
            raise ValueError(f"Cannot delete group with {hosts_count} hosts")

        # Check if group has children
        children = await cls.get_user_groups(db, self.user_id, self.id)
        if children:
            raise ValueError("Cannot delete group with subgroups")

        self.is_active = False
        self.updated_at = datetime.utcnow()
        await db.commit()

    async def restore(self, db: AsyncSession) -> None:
        """Restore soft deleted group."""
        self.is_active = True
        self.updated_at = datetime.utcnow()
        await db.commit()

    async def delete(self, db: AsyncSession) -> None:
        """Permanently delete group."""
        await db.delete(self)
        await db.commit()

    @property
    def full_path(self) -> str:
        """Get full path of group (would require DB query for parent chain)."""
        # Simplified version - in real implementation, would build full path
        return self.name

    def to_dict(self, include_children: bool = False) -> Dict[str, Any]:
        """Convert group to dictionary."""
        data = {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "parent_group_id": str(self.parent_group_id) if self.parent_group_id else None,
            "name": self.name,
            "description": self.description,
            "color": self.color,
            "icon": self.icon,
            "settings": self.settings or {},
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_active": self.is_active,
            "sort_order": self.sort_order
        }

        if include_children:
            # Children would be loaded separately in a real implementation
            data["children"] = []

        return data