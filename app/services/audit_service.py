import uuid
import structlog
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime

from app.db.unit_of_work import SQLAlchemyUnitOfWork
from app.models.audit_log import AuditLog
from app.events.definitions import (
    UserRegistered,
    UserLoggedIn,
    TransactionCreated,
    TransactionUpdated,
    TransactionDeleted,
    BudgetExceeded,
    ReportGenerated
)

logger = structlog.get_logger("app.services.audit")

class AuditService:
    """Service handling audit trail logging and admin queries."""

    def __init__(self, uow: SQLAlchemyUnitOfWork):
        self.uow = uow

    async def record_log(
        self,
        action: str,
        entity_type: str,
        entity_id: Optional[uuid.UUID] = None,
        old_data: Optional[Dict[str, Any]] = None,
        new_data: Optional[Dict[str, Any]] = None,
        user_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """Create and persist an append-only audit log entry."""
        # Retrieve correlation ID and client metadata from context variables if not provided
        ctx = structlog.contextvars.get_contextvars()
        request_id = ctx.get("request_id")
        
        if not ip_address:
            ip_address = ctx.get("ip_address")
        if not user_agent:
            user_agent = ctx.get("user_agent")

        async with self.uow:
            log_entry = AuditLog(
                user_id=user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                old_data=old_data,
                new_data=new_data,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id
            )
            await self.uow.audit.add(log_entry)
            await self.uow.commit()
            
            logger.info(
                "Audit log recorded",
                action=action,
                entity_type=entity_type,
                entity_id=str(entity_id) if entity_id else None,
                user_id=str(user_id) if user_id else None
            )
            return log_entry

    async def get_audit_logs(
        self,
        page: int = 1,
        per_page: int = 20,
        user_id: Optional[uuid.UUID] = None,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[uuid.UUID] = None,
        request_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Tuple[List[AuditLog], int]:
        """Query paginated audit logs with filtering capability (Admin-only)."""
        async with self.uow:
            items = await self.uow.audit.get_filtered(
                page=page,
                per_page=per_page,
                user_id=user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                request_id=request_id,
                date_from=date_from,
                date_to=date_to
            )
            total = await self.uow.audit.count_filtered(
                user_id=user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                request_id=request_id,
                date_from=date_from,
                date_to=date_to
            )
            return items, total

    # --- Domain Event Handlers ---

    async def on_user_registered(self, event: UserRegistered) -> None:
        """Handle UserRegistered event to audit new user account creation."""
        await self.record_log(
            action="CREATE",
            entity_type="user",
            entity_id=event.user_id,
            new_data={"email": event.email},
            user_id=event.user_id
        )

    async def on_user_logged_in(self, event: UserLoggedIn) -> None:
        """Handle UserLoggedIn event to audit user login sessions."""
        await self.record_log(
            action="LOGIN",
            entity_type="user",
            entity_id=event.user_id,
            user_id=event.user_id,
            ip_address=event.ip_address,
            user_agent=event.user_agent
        )

    async def on_transaction_created(self, event: TransactionCreated) -> None:
        """Handle TransactionCreated event to audit financial transactions creation."""
        await self.record_log(
            action="CREATE",
            entity_type="transaction",
            entity_id=event.transaction_id,
            new_data={
                "transaction_type": event.transaction_type,
                "amount": float(event.amount),
                "currency": event.currency,
                "category_id": str(event.category_id) if event.category_id else None,
                "transaction_date": event.transaction_date.isoformat(),
                "description": event.description
            },
            user_id=event.user_id
        )

    async def on_transaction_updated(self, event: TransactionUpdated) -> None:
        """Handle TransactionUpdated event to audit changes to financial records."""
        await self.record_log(
            action="UPDATE",
            entity_type="transaction",
            entity_id=event.transaction_id,
            old_data=event.old_data,
            new_data=event.new_data,
            user_id=event.user_id
        )

    async def on_transaction_deleted(self, event: TransactionDeleted) -> None:
        """Handle TransactionDeleted event to audit deletions of financial records."""
        await self.record_log(
            action="DELETE",
            entity_type="transaction",
            entity_id=event.transaction_id,
            user_id=event.user_id
        )

    async def on_budget_exceeded(self, event: BudgetExceeded) -> None:
        """Handle BudgetExceeded event to audit threshold breaches."""
        await self.record_log(
            action="BUDGET_EXCEEDED",
            entity_type="budget",
            entity_id=event.budget_id,
            new_data={
                "category_name": event.category_name,
                "limit_amount": float(event.limit_amount),
                "spent_amount": float(event.spent_amount),
                "percentage": float(event.percentage)
            },
            user_id=event.user_id
        )

    async def on_report_generated(self, event: ReportGenerated) -> None:
        """Handle ReportGenerated event to audit report generation activity."""
        await self.record_log(
            action="GENERATE_REPORT",
            entity_type="report",
            new_data={
                "report_type": event.report_type,
                "file_url": event.file_url
            },
            user_id=event.user_id
        )
