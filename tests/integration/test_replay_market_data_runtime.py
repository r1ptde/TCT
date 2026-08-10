from datetime import UTC, datetime, timedelta

import pytest

from tct_engine.domain.enums import Timeframe
from tct_engine.engine.identifiers import RandomIdGenerator
from tct_engine.engine.runtime import build_market_data_runtime
from tct_engine.events.market_data import BarClosed, BarOpened
from tct_engine.infrastructure.clock import ReplayClock
from tct_engine.ingestion.models import RawTick
from tct_engine.research.replay import ReplayEngine
from tct_engine.research.replay_source import HistoricalTickSource


@pytest.mark.asyncio
async def test_replay_produces_multi_timeframe_bars() -> None:
    start = datetime(2026, 8, 10, 8, 0, tzinfo=UTC)

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
            timestamp=start + timedelta(seconds=30),
            bid=1.1502,
            ask=1.1504,
            sequence=2,
            source="historical",
        ),
        RawTick(
            instrument="EURUSD",
            timestamp=start + timedelta(minutes=1),
            bid=1.1504,
            ask=1.1506,
            sequence=3,
            source="historical",
        ),
    ]

    clock = ReplayClock(start)

    runtime = build_market_data_runtime(
        clock=clock,
        id_generator=RandomIdGenerator(),
        timeframes=(
            Timeframe.M1,
            Timeframe.M3,
            Timeframe.M5,
            Timeframe.M15,
        ),
    )

    opened: list[BarOpened] = []
    closed: list[BarClosed] = []

    async def on_opened(event: BarOpened) -> None:
        opened.append(event)

    async def on_closed(event: BarClosed) -> None:
        closed.append(event)

    runtime.event_bus.subscribe(BarOpened, on_opened)
    runtime.event_bus.subscribe(BarClosed, on_closed)

    replay = ReplayEngine(
        source=HistoricalTickSource(ticks),
        clock=clock,
        ingestion_pipeline=runtime.ingestion_pipeline,
    )

    processed = await replay.run()

    assert processed == 3
    assert len(opened) == 5
    assert len(closed) == 1

    closed_bar = closed[0].candle

    assert closed_bar.timeframe is Timeframe.M1
    assert closed_bar.open_time == start
    assert closed_bar.close_time == start + timedelta(minutes=1)
    assert closed_bar.tick_volume == 2


@pytest.mark.asyncio
async def test_replay_preserves_bar_ohlc() -> None:
    start = datetime(2026, 8, 10, 8, 0, tzinfo=UTC)

    ticks = [
        RawTick(
            instrument="EURUSD",
            timestamp=start,
            bid=1.1000,
            ask=1.1002,
            sequence=1,
            source="historical",
        ),
        RawTick(
            instrument="EURUSD",
            timestamp=start + timedelta(seconds=10),
            bid=1.1010,
            ask=1.1012,
            sequence=2,
            source="historical",
        ),
        RawTick(
            instrument="EURUSD",
            timestamp=start + timedelta(seconds=20),
            bid=1.0990,
            ask=1.0992,
            sequence=3,
            source="historical",
        ),
        RawTick(
            instrument="EURUSD",
            timestamp=start + timedelta(seconds=30),
            bid=1.1005,
            ask=1.1007,
            sequence=4,
            source="historical",
        ),
        RawTick(
            instrument="EURUSD",
            timestamp=start + timedelta(minutes=1),
            bid=1.1007,
            ask=1.1009,
            sequence=5,
            source="historical",
        ),
    ]

    clock = ReplayClock(start)

    runtime = build_market_data_runtime(
        clock=clock,
        id_generator=RandomIdGenerator(),
        timeframes=(Timeframe.M1,),
    )

    closed: list[BarClosed] = []

    async def on_closed(event: BarClosed) -> None:
        closed.append(event)

    runtime.event_bus.subscribe(BarClosed, on_closed)

    replay = ReplayEngine(
        source=HistoricalTickSource(ticks),
        clock=clock,
        ingestion_pipeline=runtime.ingestion_pipeline,
    )

    await replay.run()

    assert len(closed) == 1

    candle = closed[0].candle

    assert candle.open == pytest.approx(1.1001)
    assert candle.high == pytest.approx(1.1011)
    assert candle.low == pytest.approx(1.0991)
    assert candle.close == pytest.approx(1.1006)
    assert candle.tick_volume == 4


@pytest.mark.asyncio
async def test_bar_closed_is_emitted_before_next_bar_opened() -> None:
    start = datetime(2026, 8, 10, 8, 0, tzinfo=UTC)

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
            timestamp=start + timedelta(minutes=1),
            bid=1.1504,
            ask=1.1506,
            sequence=2,
            source="historical",
        ),
    ]

    clock = ReplayClock(start)

    runtime = build_market_data_runtime(
        clock=clock,
        id_generator=RandomIdGenerator(),
        timeframes=(Timeframe.M1,),
    )

    trace: list[str] = []

    async def on_opened(event: BarOpened) -> None:
        trace.append("opened")

    async def on_closed(event: BarClosed) -> None:
        trace.append("closed")

    runtime.event_bus.subscribe(BarOpened, on_opened)
    runtime.event_bus.subscribe(BarClosed, on_closed)

    replay = ReplayEngine(
        source=HistoricalTickSource(ticks),
        clock=clock,
        ingestion_pipeline=runtime.ingestion_pipeline,
    )

    await replay.run()

    assert trace == [
        "opened",
        "closed",
        "opened",
    ]
