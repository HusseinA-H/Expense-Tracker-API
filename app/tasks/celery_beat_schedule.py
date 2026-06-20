from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "evaluate-all-budgets-hourly": {
        "task": "app.tasks.budget_alerts.evaluate_all_budgets",
        "schedule": crontab(minute=0),
        "options": {"queue": "default"},
    },
    "cleanup-expired-tokens-daily": {
        "task": "app.tasks.maintenance_tasks.cleanup_expired_tokens",
        "schedule": crontab(hour=0, minute=0),
        "options": {"queue": "default"},
    },
    "archive-old-partitions-monthly": {
        "task": "app.tasks.maintenance_tasks.archive_old_partitions",
        "schedule": crontab(day_of_month=1, hour=1, minute=0),
        "options": {"queue": "default"},
    },
}
