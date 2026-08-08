from __future__ import annotations

from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import TypeAlias, TypeVar

from tct_engine.events.base import Event

EventT = TypeVar("EventT", bound=Event)
EventHandler: TypeAlias = Callable[[Event], Awaitable[None]]


class EventBus:
    """Deterministic in-process asynchronous event dispatcher."""

    def __init__(self) -> None:
        self._handlers: dict[type[Event], list[EventHandler]] = defaultdict(list)

    def subscribe(
        self,
        event_type: type[EventT],
        handler: Callable[[EventT], Awaitable[None]],
    ) -> None:
        handlers = self._handlers[event_type]

        if handler in handlers:
            raise ValueError("Handler is already subscribed to this event type.")

        handlers.append(handler)  # type: ignore[arg-type]

    async def publish(self, event: Event) -> None:
        """Dispatch an event to subscribers in registration order."""

        handlers = tuple(self._handlers.get(type(event), ()))

        for handler in handlers:
            await handler(event)

    def clear(self) -> None:
        """Remove all subscriptions."""

        self._handlers.clear()
