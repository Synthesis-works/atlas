import uuid
from datetime import datetime, UTC
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Enum as SQLEnum, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
import enum
from typing import Any

from .core import Base


class TargetType(str, enum.Enum):
    BENCHMARK_VERSION = "BENCHMARK_VERSION"
    CAPABILITY = "CAPABILITY"


class LeaderboardSnapshot(Base):
    __tablename__ = "leaderboard_snapshots"
    __table_args__ = (
        Index(
            "uq_snapshot_target_exec",
            "target_id",
            text("(metadata->>'execution_id_trigger')"),
            unique=True,
            postgresql_where=text("metadata->>'execution_id_trigger' IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    target_type: Mapped[TargetType] = mapped_column(
        SQLEnum(TargetType, name="target_type_enum"), nullable=False
    )
    target_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    snapshot_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    snapshot_reason: Mapped[str] = mapped_column(String, nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)

    entries: Mapped[list["LeaderboardSnapshotEntry"]] = relationship(
        "LeaderboardSnapshotEntry", back_populates="snapshot", cascade="all, delete-orphan"
    )


class LeaderboardSnapshotEntry(Base):
    __tablename__ = "leaderboard_snapshot_entries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("leaderboard_snapshots.id"), nullable=False
    )
    target_model: Mapped[str] = mapped_column(String, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    execution_id: Mapped[uuid.UUID] = mapped_column(
        nullable=False
    )  # Not enforcing FK to allow flexible snapshot retention

    snapshot: Mapped["LeaderboardSnapshot"] = relationship(
        "LeaderboardSnapshot", back_populates="entries"
    )
