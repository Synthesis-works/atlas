import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from atlas_db.core.base import Base, BaseMixin, utcnow

class Report(Base, BaseMixin):
    __tablename__ = "reports"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    versions: Mapped[list["ReportVersion"]] = relationship("ReportVersion", back_populates="report")

class ReportVersion(Base):
    __tablename__ = "report_versions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reports.id"), nullable=False)
    version_string: Mapped[str] = mapped_column(String(50), nullable=False)
    summary: Mapped[str | None] = mapped_column(String, nullable=True)
    execution_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("executions.id"), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    report: Mapped["Report"] = relationship("Report", back_populates="versions")
    metrics: Mapped[list["ReportMetric"]] = relationship("ReportMetric", back_populates="report_version")

class ReportMetric(Base, BaseMixin):
    __tablename__ = "report_metrics"

    report_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("report_versions.id"), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(255), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)

    report_version: Mapped["ReportVersion"] = relationship("ReportVersion", back_populates="metrics")
