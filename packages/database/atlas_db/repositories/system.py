from .base import BaseRepository
from atlas_db.models.system import AuditLog, Notification

class AuditLogRepository(BaseRepository[AuditLog]):
    model = AuditLog

class NotificationRepository(BaseRepository[Notification]):
    model = Notification
