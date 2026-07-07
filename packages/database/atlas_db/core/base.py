from typing import Any
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Integer, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declared_attr

class Base(DeclarativeBase):
    """Base for all SQLAlchemy models."""
    pass

def utcnow() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)

class BaseMixin:
    """
    Standard mixin for all aggregate roots, providing standard metadata:
    - id (UUID)
    - created_at
    - updated_at
    - created_by_id
    - updated_by_id
    - archived_at
    - version_number (optimistic concurrency control)
    """
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    
    updated_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    version_number: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )

    @declared_attr
    def __mapper_args__(cls):
        return {"version_id_col": cls.version_number}
