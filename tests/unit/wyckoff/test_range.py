from datetime import UTC, datetime, timedelta

import pytest

from tct_engine.domain.enums import Timeframe
from tct_engine.domain.market_data import Candle
from tct_engine.wyckoff.range import (
    DeviationStatus,
    DeviationTracker,
    RangeSide,
    RangeStatus,
    WyckoffRange,
)


def make_candle(
    index: int,
    *,
    open_price: float,
    high: float,
    low: float,
    close: float,
) -> Candle:
    open_time = datetime(
        2026,
        8,
        19,
        8,
        0,
        tzinfo=UTC,
    ) + timedelta(minutes=index)

    return Candle(
        instrument="EURUSD",
        timeframe=Timeframe.M15,
        open_time=open_time,
        close_time=open_time + timedelta(minutes=15),
        open=open_price,
        high=high,
        low=low,
        close=close,
        tick_volume=100,
        is_closed=True,
    )


def make_accumulation_range() -> WyckoffRange:
    return WyckoffRange(
        instrument="EURUSD",
        timeframe=Timeframe.M15,
        side=RangeSide.ACCUMULATION,
        high=1.1100,
        low=1.1000,
        tap_count=1,
        status=RangeStatus.ACTIVE,
    )


def make_distribution_range() -> WyckoffRange:
    return WyckoffRange(
        instrument="EURUSD",
        timeframe=Timeframe.M15,
        side=RangeSide.DISTRIBUTION,
        high=1.1100,
        low=1.1000,
        tap_count=1,
        status=RangeStatus.ACTIVE,
    )


def test_accumulation_wick_deviation_completes_with_zero_outside_closes() -> None:
    tracker = DeviationTracker(
        wyckoff_range=make_accumulation_range(),
        lower_limit=1.0970,
        upper_limit=1.1130,
    )

    candle = make_candle(
        0,
        open_price=1.1010,
        high=1.1020,
        low=1.0990,
        close=1.1005,
    )

    deviation = tracker.process_bar(candle)

    assert deviation is not None
    assert deviation.status is DeviationStatus.COMPLETED
    assert deviation.outside_closes == 0
    assert deviation.original_boundary == 1.1000
    assert deviation.extreme == 1.0990
    assert deviation.completed_by == candle


def test_accumulation_one_outside_close_then_reentry_is_valid() -> None:
    tracker = DeviationTracker(
        wyckoff_range=make_accumulation_range(),
        lower_limit=1.0970,
        upper_limit=1.1130,
    )

    first = make_candle(
        0,
        open_price=1.1005,
        high=1.1010,
        low=1.0990,
        close=1.0995,
    )

    second = make_candle(
        1,
        open_price=1.0995,
        high=1.1010,
        low=1.0990,
        close=1.1005,
    )

    first_result = tracker.process_bar(first)

    assert first_result is not None
    assert first_result.status is DeviationStatus.IN_PROGRESS
    assert first_result.outside_closes == 1

    final_result = tracker.process_bar(second)

    assert final_result is not None
    assert final_result.status is DeviationStatus.COMPLETED
    assert final_result.outside_closes == 1
    assert final_result.completed_by == second


def test_three_outside_closes_then_fourth_candle_reenters_is_valid() -> None:
    tracker = DeviationTracker(
        wyckoff_range=make_accumulation_range(),
        lower_limit=1.0970,
        upper_limit=1.1130,
    )

    candles = [
        make_candle(
            0,
            open_price=1.1005,
            high=1.1010,
            low=1.0990,
            close=1.0995,
        ),
        make_candle(
            1,
            open_price=1.0995,
            high=1.1000,
            low=1.0985,
            close=1.0990,
        ),
        make_candle(
            2,
            open_price=1.0990,
            high=1.0995,
            low=1.0980,
            close=1.0985,
        ),
        make_candle(
            3,
            open_price=1.0985,
            high=1.1010,
            low=1.0980,
            close=1.1005,
        ),
    ]

    result = None

    for candle in candles:
        result = tracker.process_bar(candle)

    assert result is not None
    assert result.status is DeviationStatus.COMPLETED
    assert result.outside_closes == 3
    assert result.completed_by == candles[-1]


def test_fourth_outside_close_invalidates_deviation() -> None:
    tracker = DeviationTracker(
        wyckoff_range=make_accumulation_range(),
        lower_limit=1.0950,
        upper_limit=1.1150,
    )

    candles = [
        make_candle(
            0,
            open_price=1.1005,
            high=1.1010,
            low=1.0990,
            close=1.0995,
        ),
        make_candle(
            1,
            open_price=1.0995,
            high=1.1000,
            low=1.0985,
            close=1.0990,
        ),
        make_candle(
            2,
            open_price=1.0990,
            high=1.0995,
            low=1.0980,
            close=1.0985,
        ),
        make_candle(
            3,
            open_price=1.0985,
            high=1.0990,
            low=1.0975,
            close=1.0980,
        ),
    ]

    result = None

    for candle in candles:
        result = tracker.process_bar(candle)

    assert result is not None
    assert result.status is DeviationStatus.INVALIDATED
    assert result.outside_closes == 4
    assert result.invalidated_by == candles[-1]


def test_close_beyond_lower_deviation_limit_invalidates_accumulation() -> None:
    tracker = DeviationTracker(
        wyckoff_range=make_accumulation_range(),
        lower_limit=1.0970,
        upper_limit=1.1130,
    )

    candle = make_candle(
        0,
        open_price=1.1000,
        high=1.1005,
        low=1.0960,
        close=1.0965,
    )

    deviation = tracker.process_bar(candle)

    assert deviation is not None
    assert deviation.status is DeviationStatus.INVALIDATED
    assert deviation.invalidated_by == candle


def test_wick_beyond_lower_limit_does_not_invalidate_if_close_is_within_limit() -> None:
    tracker = DeviationTracker(
        wyckoff_range=make_accumulation_range(),
        lower_limit=1.0970,
        upper_limit=1.1130,
    )

    candle = make_candle(
        0,
        open_price=1.1000,
        high=1.1005,
        low=1.0960,
        close=1.0980,
    )

    deviation = tracker.process_bar(candle)

    assert deviation is not None
    assert deviation.status is DeviationStatus.IN_PROGRESS
    assert deviation.outside_closes == 1
    assert deviation.extreme == 1.0960


def test_deviation_tracks_deepest_wick() -> None:
    tracker = DeviationTracker(
        wyckoff_range=make_accumulation_range(),
        lower_limit=1.0950,
        upper_limit=1.1150,
    )

    first = make_candle(
        0,
        open_price=1.1005,
        high=1.1010,
        low=1.0990,
        close=1.0995,
    )

    second = make_candle(
        1,
        open_price=1.0995,
        high=1.1000,
        low=1.0975,
        close=1.0985,
    )

    third = make_candle(
        2,
        open_price=1.0985,
        high=1.1010,
        low=1.0980,
        close=1.1005,
    )

    tracker.process_bar(first)
    tracker.process_bar(second)
    deviation = tracker.process_bar(third)

    assert deviation is not None
    assert deviation.status is DeviationStatus.COMPLETED
    assert deviation.extreme == 1.0975


def test_distribution_wick_deviation_is_symmetric() -> None:
    tracker = DeviationTracker(
        wyckoff_range=make_distribution_range(),
        lower_limit=1.0970,
        upper_limit=1.1130,
    )

    candle = make_candle(
        0,
        open_price=1.1090,
        high=1.1110,
        low=1.1080,
        close=1.1095,
    )

    deviation = tracker.process_bar(candle)

    assert deviation is not None
    assert deviation.status is DeviationStatus.COMPLETED
    assert deviation.outside_closes == 0
    assert deviation.original_boundary == 1.1100
    assert deviation.extreme == 1.1110


def test_distribution_close_beyond_upper_limit_invalidates() -> None:
    tracker = DeviationTracker(
        wyckoff_range=make_distribution_range(),
        lower_limit=1.0970,
        upper_limit=1.1130,
    )

    candle = make_candle(
        0,
        open_price=1.1100,
        high=1.1140,
        low=1.1090,
        close=1.1135,
    )

    deviation = tracker.process_bar(candle)

    assert deviation is not None
    assert deviation.status is DeviationStatus.INVALIDATED
    assert deviation.invalidated_by == candle


def test_distribution_three_closes_then_reentry_is_valid() -> None:
    tracker = DeviationTracker(
        wyckoff_range=make_distribution_range(),
        lower_limit=1.0950,
        upper_limit=1.1150,
    )

    candles = [
        make_candle(
            0,
            open_price=1.1095,
            high=1.1110,
            low=1.1090,
            close=1.1105,
        ),
        make_candle(
            1,
            open_price=1.1105,
            high=1.1120,
            low=1.1100,
            close=1.1110,
        ),
        make_candle(
            2,
            open_price=1.1110,
            high=1.1130,
            low=1.1105,
            close=1.1120,
        ),
        make_candle(
            3,
            open_price=1.1120,
            high=1.1125,
            low=1.1090,
            close=1.1095,
        ),
    ]

    result = None

    for candle in candles:
        result = tracker.process_bar(candle)

    assert result is not None
    assert result.status is DeviationStatus.COMPLETED
    assert result.outside_closes == 3


def test_open_bar_is_rejected() -> None:
    tracker = DeviationTracker(
        wyckoff_range=make_accumulation_range(),
        lower_limit=1.0970,
        upper_limit=1.1130,
    )

    closed = make_candle(
        0,
        open_price=1.1000,
        high=1.1010,
        low=1.0990,
        close=1.1005,
    )

    open_candle = Candle(
        instrument=closed.instrument,
        timeframe=closed.timeframe,
        open_time=closed.open_time,
        close_time=closed.close_time,
        open=closed.open,
        high=closed.high,
        low=closed.low,
        close=closed.close,
        tick_volume=closed.tick_volume,
        is_closed=False,
    )

    with pytest.raises(ValueError, match="closed candle"):
        tracker.process_bar(open_candle)
