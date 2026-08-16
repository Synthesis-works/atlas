from atlas_db.models.reporting import Report, ReportMetric, ReportVersion

from .base import BaseRepository


class ReportRepository(BaseRepository[Report]):
    model = Report


class ReportVersionRepository(BaseRepository[ReportVersion]):
    model = ReportVersion


class ReportMetricRepository(BaseRepository[ReportMetric]):
    model = ReportMetric
