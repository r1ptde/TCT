from datetime import UTC, datetime
from uuid import UUID

import pytest

from tct_engine.engine.event_bus import EventBus
from tct_engine.engine.identifiers import FixedSequenceIdGenerator
from tct_engine.events.market_data import (
    TickReceived,
    TickRejected,
    TickValidated,
)
from tct_engine.infrastructure.clock import FixedClock
from tct_engine.ingestion.models import RawTick
from tct_engine.ingestion.pipeline import TickIngestionPipeline
from tct_engine.ingestion.validation import TickRejectionReason


def make_ids() -> list[UUID]:
    return [
        UUID("00000000-0000-0000-0000-000000000001"),
        UUID("00000000-0000-0000-0000-000000000002"),
        UUID("00000000-0000-0000-0000-000000000003"),
    ]


@pytest.mark.asyncio
async def test_valid_raw_tick_emits_received_then_validated() -> None:
    event_bus = EventBus()
    observed: list[str] = []

    async def on_received(event: TickReceived) -> None:
        observed.append("received")

    async def on_validated(event: TickValidated) -> None:
        observed.append("validated")

    event_bus.subscribe(TickReceived, on_received)
    event_bus.subscribe(TickValidated, on_validated)

    timestamp = datetime(2026, 8, 8, 8, 0, tzinfo=UTC)

    pipeline = TickIngestionPipeline(
        event_bus=event_bus,
        clock=FixedClock(timestamp),
        id_generator=FixedSequenceIdGenerator(make_ids()),
    )

    await pipeline.process(
        RawTick(
            instrument=" eurusd ",
            timestamp=timestamp,
            bid=1.1500,
            ask=1.1502,
            sequence=1,
            source="test-feed",
        )
    )

    assert observed == ["received", "validated"]


@pytest.mark.asyncio
async def test_invalid_raw_tick_emits_received_then_rejected() -> None:
    event_bus = EventBus()
    rejection_reasons: list[TickRejectionReason] = []

    async def on_rejected(event: TickRejected) -> None:
        rejection_reasons.append(event.reason)

    event_bus.subscribe(TickRejected, on_rejected)

    timestamp = datetime(2026, 8, 8, 8, 0, tzinfo=UTC)

    pipeline = TickIngestionPipeline(
        event_bus=event_bus,
        clock=FixedClock(timestamp),
        id_generator=FixedSequenceIdGenerator(make_ids()),
    )

    await pipeline.process(
        RawTick(
            instrument="EURUSD",
            timestamp=timestamp,
            bid=1.1503,
            ask=1.1502,
            sequence=1,
            source="test-feed",
        )
    )

    assert rejection_reasons == [TickRejectionReason.CROSSED_MARKET]


@pytest.mark.asyncio
async def test_validated_event_is_caused_by_received_event() -> None:
    event_bus = EventBus()
    received_ids: list[UUID] = []
    causation_ids: list[UUID | None] = []

    async def on_received(event: TickReceived) -> None:
        received_ids.append(event.event_id)

    async def on_validated(event: TickValidated) -> None:
        causation_ids.append(event.causation_id)

    event_bus.subscribe(TickReceived, on_received)
    event_bus.subscribe(TickValidated, on_validated)

    timestamp = datetime(2026, 8, 8, 8, 0, tzinfo=UTC)

    pipeline = TickIngestionPipeline(
        event_bus=event_bus,
        clock=FixedClock(timestamp),
        id_generator=FixedSequenceIdGenerator(make_ids()),
    )

    await pipeline.process(
        RawTick(
            instrument="EURUSD",
            timestamp=timestamp,
            bid=1.1500,
            ask=1.1502,
        )
    )

    assert causation_ids == received_ids


@pytest.mark.asyncio
async def test_pipeline_normalizes_instrument_before_emission() -> None:
    event_bus = EventBus()
    instruments: list[str] = []

    async def on_validated(event: TickValidated) -> None:
        instruments.append(event.tick.instrument)

    event_bus.subscribe(TickValidated, on_validated)

    timestamp = datetime(2026, 8, 8, 8, 0, tzinfo=UTC)

    pipeline = TickIngestionPipeline(
        event_bus=event_bus,
        clock=FixedClock(timestamp),
        id_generator=FixedSequenceIdGenerator(make_ids()),
    )

    await pipeline.process(
        RawTick(
            instrument=" eurusd ",
            timestamp=timestamp,
            bid=1.1500,
            ask=1.1502,
        )
    )

    assert instruments == ["EURUSD"]
