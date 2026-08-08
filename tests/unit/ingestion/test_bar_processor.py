from datetime import UTC, datetime
from uuid import UUID

import pytest

from tct_engine.domain.enums import Timeframe
from tct_engine.domain.market_data import Tick
from tct_engine.engine.event_bus import EventBus
from tct_engine.engine.identifiers import FixedSequenceIdGenerator
from tct_engine.events.market_data import (
    BarOpened,
    TickValidated,
)
from tct_engine.infrastructure.clock import FixedClock
from tct_engine.ingestion.bar_processor import BarAggregationProcessor


@pytest.mark.asyncio
async def test_processor_emits_bar_opened() -> None:
    event_bus = EventBus()
    observed: list[BarOpened] = []

    async def on_opened(event: BarOpened) -> None:
        observed.append(event)

    event_bus.subscribe(BarOpened, on_opened)

    timestamp = datetime(2026, 8, 8, 8, 0, 10, tzinfo=UTC)

    processor = BarAggregationProcessor(
        event_bus=event_bus,
        clock=FixedClock(timestamp),
        id_generator=FixedSequenceIdGenerator(
            [
                UUID("00000000-0000-0000-0000-000000000010"),
            ]
        ),
        timeframes=(Timeframe.M1,),
    )

    tick_event = TickValidated(
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

    await processor.on_tick_validated(tick_event)

    assert len(observed) == 1
    assert observed[0].candle.timeframe is Timeframe.M1
