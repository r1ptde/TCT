from datetime import UTC, datetime

from tct_engine.domain.enums import Timeframe
from tct_engine.domain.market_data import Tick


def test_tick_mid_price() -> None:
    tick = Tick(
        instrument="EURUSD",
        timestamp=datetime(2026, 8, 7, 8, 0, tzinfo=UTC),
        bid=1.1500,
        ask=1.1502,
    )

    assert tick.mid == 1.1501


def test_tick_spread() -> None:
    tick = Tick(
        instrument="EURUSD",
        timestamp=datetime(2026, 8, 7, 8, 0, tzinfo=UTC),
        bid=1.1500,
        ask=1.1502,
    )

    assert round(tick.spread, 4) == 0.0002


def test_timeframe_seconds() -> None:
    assert Timeframe.M1.seconds == 60
    assert Timeframe.M3.seconds == 180
    assert Timeframe.M15.seconds == 900
