from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from tct_engine.engine.event_bus import EventBus
from tct_engine.engine.identifiers import FixedSequenceIdGenerator
from tct_engine.events.market_data import TickValidated
from tct_engine.infrastructure.clock import ReplayClock
from tct_engine.ingestion.models import RawTick
from tct_engine.ingestion.pipeline import TickIngestionPipeline
from tct_engine.research.replay import ReplayEngine
from tct_engine.research.replay_source import HistoricalTickSource


@pytest.mark.asyncio
async def test_replay_advances_clock_and_processes_ticks() -> None:
    start = datetime(2026, 8, 10, 8, 0, tzinfo=UTC)
    second = start + timedelta(seconds=1)

    ticks = [
        RawTick(
            instrument="EURUSD",
            timestamp=start,
            bid=1.1500,
            ask=1.1502,
            sequence=1,
            source="historical",
        ),
        RawTick(
            instrument="EURUSD",
            timestamp=second,
            bid=1.1501,
            ask=1.1503,
            sequence=2,
            source="historical",
        ),
    ]

    bus = EventBus()
    observed: list[TickValidated] = []

    async def on_validated(event: TickValidated) -> None:
        observed.append(event)

    bus.subscribe(TickValidated, on_validated)

    clock = ReplayClock(start)

    pipeline = TickIngestionPipeline(
        event_bus=bus,
        clock=clock,
        id_generator=FixedSequenceIdGenerator(
            [
                UUID("00000000-0000-0000-0000-000000000001"),
                UUID("00000000-0000-0000-0000-000000000002"),
                UUID("00000000-0000-0000-0000-000000000003"),
                UUID("00000000-0000-0000-0000-000000000004"),
            ]
        ),
    )

    replay = ReplayEngine(
        source=HistoricalTickSource(ticks),
        clock=clock,
        ingestion_pipeline=pipeline,
    )

    processed = await replay.run()

    assert processed == 2
    assert len(observed) == 2
    assert clock.now() == second
