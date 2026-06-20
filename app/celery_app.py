import os
from celery import Celery
from app.config import settings

# Dynamically discover available task modules
include_modules = []
tasks_dir = os.path.join(os.path.dirname(__file__), "tasks")
if os.path.exists(tasks_dir):
    for f in os.listdir(tasks_dir):
        if f.endswith(".py") and f != "__init__.py" and f != "celery_beat_schedule.py":
            include_modules.append(f"app.tasks.{f[:-3]}")

celery_app = Celery(
    "expense_tracker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=include_modules
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_queue="default",
    task_routes={
        "app.tasks.email_tasks.*": {"queue": "email"},
    },
)

try:
    from app.tasks.celery_beat_schedule import CELERY_BEAT_SCHEDULE
    celery_app.conf.beat_schedule = CELERY_BEAT_SCHEDULE
except ImportError:
    pass


@celery_app.on_after_configure.connect
def configure_celery_telemetry(sender, **kwargs):
    from app.core.telemetry import setup_telemetry

    setup_telemetry("expense-tracker-celery")
