from datetime import UTC, datetime, timedelta

from tct_engine.domain.enums import Timeframe
from tct_engine.domain.market_data import Tick
from tct_engine.ingestion.aggregator import BarAggregator


def make_tick(
    *,
    timestamp: datetime,
    bid: float,
    ask: float,
) -> Tick:
    return Tick(
        instrument="EURUSD",
        timestamp=timestamp,
        bid=bid,
        ask=ask,
        source="test-feed",
    )


def test_first_tick_opens_new_bar() -> None:
    aggregator = BarAggregator(Timeframe.M1)

    timestamp = datetime(2026, 8, 8, 8, 0, 10, tzinfo=UTC)

    closed, current = aggregator.process_tick(
        make_tick(
            timestamp=timestamp,
            bid=1.1500,
            ask=1.1502,
        )
    )

    assert closed is None
    assert current.open_time == datetime(2026, 8, 8, 8, 0, tzinfo=UTC)
    assert current.close_time == datetime(2026, 8, 8, 8, 1, tzinfo=UTC)
    assert current.tick_volume == 1
    assert not current.is_closed


def test_tick_updates_active_bar() -> None:
    aggregator = BarAggregator(Timeframe.M1)

    start = datetime(2026, 8, 8, 8, 0, 10, tzinfo=UTC)

    aggregator.process_tick(make_tick(timestamp=start, bid=1.1500, ask=1.1502))

    closed, current = aggregator.process_tick(
        make_tick(
            timestamp=start + timedelta(seconds=10),
            bid=1.1504,
            ask=1.1506,
        )
    )

    assert closed is None
    assert current.high == 1.1505
    assert current.close == 1.1505
    assert current.tick_volume == 2


def test_new_interval_closes_previous_bar() -> None:
    aggregator = BarAggregator(Timeframe.M1)

    first_time = datetime(2026, 8, 8, 8, 0, 10, tzinfo=UTC)

    aggregator.process_tick(
        make_tick(
            timestamp=first_time,
            bid=1.1500,
            ask=1.1502,
        )
    )

    closed, current = aggregator.process_tick(
        make_tick(
            timestamp=datetime(2026, 8, 8, 8, 1, 0, tzinfo=UTC),
            bid=1.1510,
            ask=1.1512,
        )
    )

    assert closed is not None
    assert closed.is_closed
    assert closed.close_time == datetime(2026, 8, 8, 8, 1, tzinfo=UTC)

    assert current.open_time == datetime(2026, 8, 8, 8, 1, tzinfo=UTC)
    assert not current.is_closed


def test_m3_alignment() -> None:
    aggregator = BarAggregator(Timeframe.M3)

    timestamp = datetime(2026, 8, 8, 8, 5, 30, tzinfo=UTC)

    _, current = aggregator.process_tick(
        make_tick(
            timestamp=timestamp,
            bid=1.1500,
            ask=1.1502,
        )
    )

    assert current.open_time == datetime(2026, 8, 8, 8, 3, tzinfo=UTC)
    assert current.close_time == datetime(2026, 8, 8, 8, 6, tzinfo=UTC)
