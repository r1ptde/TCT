from datetime import UTC, datetime
from uuid import UUID

import pytest

from tct_engine.domain.market_data import Tick
from tct_engine.engine.event_bus import EventBus
from tct_engine.events.market_data import TickReceived


def make_event() -> TickReceived:
    timestamp = datetime(2026, 8, 8, 8, 0, tzinfo=UTC)

    return TickReceived(
        event_id=UUID("00000000-0000-0000-0000-000000000001"),
        occurred_at=timestamp,
        emitted_at=timestamp,
        source="unit-test",
        tick=Tick(
            instrument="EURUSD",
            timestamp=timestamp,
            bid=1.1500,
            ask=1.1502,
        ),
    )


@pytest.mark.asyncio
async def test_publish_calls_subscriber() -> None:
    bus = EventBus()
    received: list[TickReceived] = []

    async def handler(event: TickReceived) -> None:
        received.append(event)

    bus.subscribe(TickReceived, handler)

    event = make_event()

    await bus.publish(event)

    assert received == [event]


@pytest.mark.asyncio
async def test_handlers_execute_in_subscription_order() -> None:
    bus = EventBus()
    execution_order: list[str] = []

    async def first_handler(event: TickReceived) -> None:
        execution_order.append("first")

    async def second_handler(event: TickReceived) -> None:
        execution_order.append("second")

    bus.subscribe(TickReceived, first_handler)
    bus.subscribe(TickReceived, second_handler)

    await bus.publish(make_event())

    assert execution_order == ["first", "second"]


def test_duplicate_subscription_is_rejected() -> None:
    bus = EventBus()

    async def handler(event: TickReceived) -> None:
        pass

    bus.subscribe(TickReceived, handler)

    with pytest.raises(ValueError, match="already subscribed"):
        bus.subscribe(TickReceived, handler)


@pytest.mark.asyncio
async def test_unsubscribed_event_is_safe() -> None:
    bus = EventBus()

    await bus.publish(make_event())


@pytest.mark.asyncio
async def test_handler_finishes_before_next_handler_starts() -> None:
    bus = EventBus()
    trace: list[str] = []

    async def first_handler(event: TickReceived) -> None:
        trace.append("first-start")
        trace.append("first-end")

    async def second_handler(event: TickReceived) -> None:
        trace.append("second-start")
        trace.append("second-end")

    bus.subscribe(TickReceived, first_handler)
    bus.subscribe(TickReceived, second_handler)

    await bus.publish(make_event())

    assert trace == [
        "first-start",
        "first-end",
        "second-start",
        "second-end",
    ]
