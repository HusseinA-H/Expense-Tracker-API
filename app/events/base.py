import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List, Type

import structlog

logger = structlog.get_logger("app.events")


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """Base class for all domain events."""

    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class EventBus:
    """Simple in-process async event bus. NOT a distributed message broker."""

    def __init__(self):
        self._handlers: Dict[Type[DomainEvent], List[Callable]] = {}

    def subscribe(self, event_type: Type[DomainEvent], handler: Callable) -> None:
        """Register a handler for a specific event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)

    async def publish(self, event: DomainEvent) -> None:
        """Publish an event to all registered handlers asynchronously."""
        handlers = self._handlers.get(type(event), [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(
                    "Event handler failed",
                    event_type=type(event).__name__,
                    handler=(
                        handler.__name__
                        if hasattr(handler, "__name__")
                        else str(handler)
                    ),
                    error=str(e),
                    exc_info=True,
                )


# Global event bus singleton instance
event_bus = EventBus()
