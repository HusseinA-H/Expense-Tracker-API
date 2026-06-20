# Implementation Plan — Week 8: Background Jobs (Celery)

This phase moves long-running and external network tasks (email delivery, budget alerting, CSV/report generation, receipt processing) out of the request-response lifecycle and into Celery background tasks.

## User Review Required

> [!IMPORTANT]
> - Celery workers will execute in separate Docker containers. Local file systems for uploads or CSV exports must be shared between the API and Worker containers if local storage is used. In this local development stack, docker-compose mounts the host project directory to `/app` in both the `api` and `celery-worker` / `celery-beat` containers, which satisfies this requirement.
> - The SMTP configuration is set to Mailtrap in the development environment. We will use a mock SMTP server or connection failures will log warnings if the SMTP server is unreachable.

## Open Questions

None. The Celery configuration and task specifications are clearly detailed in the Architecture Document.

## Proposed Changes

---

### Email Service

#### [NEW] [email_service.py](file:///f:/CV/Expense%20Tracker%20API/app/services/email_service.py)
Create a helper service to construct and send mime messages via SMTP, supporting HTML templates for welcome emails, password resets, and budget alerts.

---

### Celery Tasks

#### [NEW] [email_tasks.py](file:///f:/CV/Expense%20Tracker%20API/app/tasks/email_tasks.py)
Implement tasks for sending emails:
- `send_welcome_email(user_id: str)`
- `send_password_reset_email(email: str, token: str)`
- `send_budget_alert_email(user_id: str, budget_id: str, limit_amount: float, spent_amount: float)`

#### [NEW] [budget_alerts.py](file:///f:/CV/Expense%20Tracker%20API/app/tasks/budget_alerts.py)
Implement `evaluate_all_budgets()` task which scans all active budgets for the current month and triggers a budget alert if limit is exceeded, publishing the `BudgetExceeded` domain event.

#### [NEW] [report_tasks.py](file:///f:/CV/Expense%20Tracker%20API/app/tasks/report_tasks.py)
Implement async report export tasks:
- `generate_csv_export(user_id: str, start_date: str, end_date: str)`
- `generate_monthly_report(user_id: str, month: int, year: int)`

#### [NEW] [receipt_tasks.py](file:///f:/CV/Expense%20Tracker%20API/app/tasks/receipt_tasks.py)
Implement `process_receipt_image(transaction_id: str, file_path: str)` to run post-upload actions such as validating image integrity, extracting metadata, and generating a thumbnail if Pillow is available.

#### [NEW] [maintenance_tasks.py](file:///f:/CV/Expense%20Tracker%20API/app/tasks/maintenance_tasks.py)
Implement maintenance tasks:
- `cleanup_expired_tokens()`
- `archive_old_partitions()` (stubbed with partition metadata checks or table cleaning logic since partition creation runs on database schedule).

#### [NEW] [celery_beat_schedule.py](file:///f:/CV/Expense%20Tracker%20API/app/tasks/celery_beat_schedule.py)
Define the periodic tasks schedule (budget alerts evaluation hourly, token cleaning daily, log archival monthly).

---

### Event Handlers Integration

#### [MODIFY] [handlers.py](file:///f:/CV/Expense%20Tracker%20API/app/events/handlers.py)
Wire event handlers to trigger background tasks:
- `handle_user_registered` -> dispatch `send_welcome_email.delay`
- `handle_budget_exceeded` -> dispatch `send_budget_alert_email.delay`

---

### Verification Plan

### Automated Tests
- Create [test_celery.py](file:///f:/CV/Expense%20Tracker%20API/tests/integration/test_celery.py) to:
  - Test task execution directly in eager mode (`CELERY_TASK_ALWAYS_EAGER = True`).
  - Verify email task composition, Celery Beat task execution, and CSV export file generation.

### Manual Verification
- Deploy/restart Docker compose stack.
- Check Flower UI at `http://localhost:5555` to confirm worker connectivity and task registration.
