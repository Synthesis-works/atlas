from .base import BaseRepository
from atlas_db.models.reporting import Report, ReportVersion, ReportMetric

class ReportRepository(BaseRepository[Report]):
    model = Report

class ReportVersionRepository(BaseRepository[ReportVersion]):
    model = ReportVersion

class ReportMetricRepository(BaseRepository[ReportMetric]):
    model = ReportMetric
