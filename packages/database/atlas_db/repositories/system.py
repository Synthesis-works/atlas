from atlas_db.models.system import AuditLog, Notification

from .base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    model = AuditLog


class NotificationRepository(BaseRepository[Notification]):
    model = Notification
