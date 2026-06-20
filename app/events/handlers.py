import uuid

import structlog

from app.db.unit_of_work import SQLAlchemyUnitOfWork
from app.events.base import event_bus
from app.events.definitions import (
    BudgetExceeded,
    PasswordChanged,
    ReportGenerated,
    TransactionCreated,
    TransactionDeleted,
    TransactionUpdated,
    UserDeactivated,
    UserLoggedIn,
    UserRegistered,
)
from app.services.audit_service import AuditService
from app.services.budget_service import BudgetService

logger = structlog.get_logger("app.events.handlers")

# --- Event Handlers ---


async def handle_user_registered(event: UserRegistered) -> None:
    uow = SQLAlchemyUnitOfWork()
    audit_service = AuditService(uow)
    try:
        await audit_service.on_user_registered(event)
    except Exception as e:
        logger.error("Error in handle_user_registered", error=str(e), exc_info=True)

    try:
        from app.tasks.email_tasks import send_welcome_email

        send_welcome_email.delay(str(event.user_id))
    except Exception as e:
        logger.error(
            "Failed to dispatch welcome email task", error=str(e), exc_info=True
        )


async def handle_user_logged_in(event: UserLoggedIn) -> None:
    uow = SQLAlchemyUnitOfWork()
    audit_service = AuditService(uow)
    try:
        await audit_service.on_user_logged_in(event)
    except Exception as e:
        logger.error("Error in handle_user_logged_in", error=str(e), exc_info=True)


async def handle_transaction_created(event: TransactionCreated) -> None:
    uow = SQLAlchemyUnitOfWork()
    audit_service = AuditService(uow)
    budget_service = BudgetService(uow)

    # 1. Record Audit Log
    try:
        await audit_service.on_transaction_created(event)
    except Exception as e:
        logger.error("Error auditing transaction creation", error=str(e), exc_info=True)

    # 2. Check Budget Threshold (Only for expenses)
    if event.transaction_type == "expense" and event.category_id is not None:
        try:
            await budget_service.check_budget_threshold(
                user_id=event.user_id,
                category_id=event.category_id,
                month=event.transaction_date.month,
                year=event.transaction_date.year,
            )
        except Exception as e:
            logger.error(
                "Error checking budget threshold on transaction creation",
                error=str(e),
                exc_info=True,
            )


async def handle_transaction_updated(event: TransactionUpdated) -> None:
    uow = SQLAlchemyUnitOfWork()
    audit_service = AuditService(uow)
    budget_service = BudgetService(uow)

    # 1. Record Audit Log
    try:
        await audit_service.on_transaction_updated(event)
    except Exception as e:
        logger.error("Error auditing transaction update", error=str(e), exc_info=True)

    # 2. Check Budget Threshold for the new details (if transaction type is expense)
    # The event contains old_data and new_data
    new_type = (
        event.new_data.get("transaction_type") or "expense"
    )  # fallback or default
    new_cat_id_str = event.new_data.get("category_id")
    new_date_str = event.new_data.get("transaction_date")

    if new_type == "expense" and new_cat_id_str and new_date_str:
        try:
            from datetime import date

            new_cat_id = (
                uuid.UUID(new_cat_id_str)
                if isinstance(new_cat_id_str, str)
                else new_cat_id_str
            )
            new_date = (
                date.fromisoformat(new_date_str)
                if isinstance(new_date_str, str)
                else new_date_str
            )

            await budget_service.check_budget_threshold(
                user_id=event.user_id,
                category_id=new_cat_id,
                month=new_date.month,
                year=new_date.year,
            )
        except Exception as e:
            logger.error(
                "Error checking budget threshold on transaction update",
                error=str(e),
                exc_info=True,
            )


async def handle_transaction_deleted(event: TransactionDeleted) -> None:
    uow = SQLAlchemyUnitOfWork()
    audit_service = AuditService(uow)
    try:
        await audit_service.on_transaction_deleted(event)
    except Exception as e:
        logger.error("Error auditing transaction deletion", error=str(e), exc_info=True)


async def handle_budget_exceeded(event: BudgetExceeded) -> None:
    uow = SQLAlchemyUnitOfWork()
    audit_service = AuditService(uow)
    try:
        await audit_service.on_budget_exceeded(event)
    except Exception as e:
        logger.error("Error auditing budget exceed event", error=str(e), exc_info=True)

    try:
        from app.tasks.email_tasks import send_budget_alert_email

        send_budget_alert_email.delay(
            str(event.user_id),
            str(event.budget_id),
            float(event.limit_amount),
            float(event.spent_amount),
        )
    except Exception as e:
        logger.error(
            "Failed to dispatch budget alert email task", error=str(e), exc_info=True
        )


async def handle_report_generated(event: ReportGenerated) -> None:
    uow = SQLAlchemyUnitOfWork()
    audit_service = AuditService(uow)
    try:
        await audit_service.on_report_generated(event)
    except Exception as e:
        logger.error("Error auditing report generation", error=str(e), exc_info=True)


async def handle_password_changed(event: PasswordChanged) -> None:
    uow = SQLAlchemyUnitOfWork()
    audit_service = AuditService(uow)
    try:
        await audit_service.record_log(
            action="PASSWORD_CHANGE",
            entity_type="user",
            entity_id=event.user_id,
            user_id=event.user_id,
        )
    except Exception as e:
        logger.error("Error auditing password change", error=str(e), exc_info=True)


async def handle_user_deactivated(event: UserDeactivated) -> None:
    uow = SQLAlchemyUnitOfWork()
    audit_service = AuditService(uow)
    try:
        await audit_service.record_log(
            action="DELETE",
            entity_type="user",
            entity_id=event.user_id,
            user_id=event.user_id,
        )
    except Exception as e:
        logger.error("Error auditing user deactivation", error=str(e), exc_info=True)


# --- Registration ---


def register_event_handlers() -> None:
    """Subscribe all domain event handlers to the global event bus."""
    event_bus.subscribe(UserRegistered, handle_user_registered)
    event_bus.subscribe(UserLoggedIn, handle_user_logged_in)
    event_bus.subscribe(TransactionCreated, handle_transaction_created)
    event_bus.subscribe(TransactionUpdated, handle_transaction_updated)
    event_bus.subscribe(TransactionDeleted, handle_transaction_deleted)
    event_bus.subscribe(BudgetExceeded, handle_budget_exceeded)
    event_bus.subscribe(ReportGenerated, handle_report_generated)
    event_bus.subscribe(PasswordChanged, handle_password_changed)
    event_bus.subscribe(UserDeactivated, handle_user_deactivated)
    logger.info("Domain event handlers registered successfully")
