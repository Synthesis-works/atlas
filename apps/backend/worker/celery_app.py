from celery import Celery
from celery.signals import task_prerun, task_postrun
import structlog
from apps.backend.config import settings
from apps.backend.core.logging import setup_logging

# Ensure logging is setup in the worker process
setup_logging()

celery_app = Celery(
    "atlas_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["apps.backend.worker.tasks"]
)

celery_app.conf.update(
    task_always_eager=settings.celery_task_always_eager,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Example concurrency / prefetch limits
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
    beat_schedule={
        "outbox-sweep": {
            "task": "apps.backend.worker.tasks.outbox_sweep_task",
            "schedule": settings.outbox_poll_interval,
        }
    }
)

@task_prerun.connect
def setup_structlog_context(task_id, task, *args, **kwargs):
    # Bind celery_task_id and correlation_id (if passed in kwargs)
    kwargs_dict = kwargs.get('kwargs', {})
    correlation_id = kwargs_dict.get('correlation_id', task_id)
    structlog.contextvars.bind_contextvars(
        celery_task_id=task_id,
        correlation_id=correlation_id,
        celery_task_name=task.name
    )

@task_postrun.connect
def clear_structlog_context(task_id, task, *args, **kwargs):
    structlog.contextvars.clear_contextvars()
