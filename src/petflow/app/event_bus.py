from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable

from petflow.domain.enums import EventType
from petflow.domain.events import DomainEvent


EventHandler = Callable[[DomainEvent], None]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[EventType, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)

    def publish(self, event: DomainEvent) -> None:
        for handler in list(self._handlers.get(event.type, [])):
            handler(event)

