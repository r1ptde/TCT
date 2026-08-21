from datetime import UTC, datetime, timedelta

from tct_engine.domain.enums import Timeframe
from tct_engine.domain.market_data import Candle
from tct_engine.wyckoff.range import (
    RangeSide,
    RangeStatus,
    WyckoffRange,
)
from tct_engine.wyckoff.taps import (
    TapModelStatus,
    TapStateMachine,
)

START = datetime(2026, 8, 21, 8, 0, tzinfo=UTC)


def make_candle(
    index: int,
    *,
    high: float,
    low: float,
    close: float,
    open_price: float | None = None,
) -> Candle:
    open_time = START + timedelta(minutes=15 * index)

    return Candle(
        instrument="EURUSD",
        timeframe=Timeframe.M15,
        open_time=open_time,
        close_time=open_time + timedelta(minutes=15),
        open=close if open_price is None else open_price,
        high=high,
        low=low,
        close=close,
        tick_volume=100,
        is_closed=True,
    )


def make_machine() -> TapStateMachine:
    wyckoff_range = WyckoffRange(
        instrument="EURUSD",
        timeframe=Timeframe.M15,
        side=RangeSide.ACCUMULATION,
        high=1.1100,
        low=1.1000,
        tap_count=1,
        status=RangeStatus.ACTIVE,
    )

    tap_1 = make_candle(
        0,
        high=1.1010,
        low=1.1000,
        close=1.1005,
    )

    return TapStateMachine(
        wyckoff_range=wyckoff_range,
        tap_1_candle=tap_1,
        lower_limit=1.0950,
        upper_limit=1.1150,
    )


def test_completed_tap_two_updates_range_low() -> None:
    machine = make_machine()

    tap_2 = make_candle(
        8,
        high=1.1010,
        low=1.0980,
        close=1.1005,
    )

    state = machine.process_bar(tap_2)

    assert state.tap_2 is not None
    assert state.tap_2.price == 1.0980
    assert state.wyckoff_range.low == 1.0980
    assert state.wyckoff_range.high == 1.1100
    assert state.wyckoff_range.tap_count == 2
    assert state.status is TapModelStatus.WATCHING_TAP_3


def test_tap_three_arms_bos_search_immediately_on_deviation() -> None:
    machine = make_machine()

    machine.process_bar(
        make_candle(
            8,
            high=1.1010,
            low=1.0980,
            close=1.1005,
        )
    )

    tap_3_start = make_candle(
        12,
        high=1.0990,
        low=1.0970,
        close=1.0975,
    )

    state = machine.process_bar(tap_3_start)

    assert state.status is TapModelStatus.TAP_3_ACTIVE
    assert state.bos_search_armed is True
    assert state.tap_3 is None


def test_completed_tap_three_updates_range_low() -> None:
    machine = make_machine()

    machine.process_bar(
        make_candle(
            8,
            high=1.1010,
            low=1.0980,
            close=1.1005,
        )
    )

    machine.process_bar(
        make_candle(
            12,
            high=1.0990,
            low=1.0970,
            close=1.0975,
        )
    )

    state = machine.process_bar(
        make_candle(
            13,
            high=1.1010,
            low=1.0965,
            close=1.0990,
        )
    )

    assert state.tap_3 is not None
    assert state.tap_3.price == 1.0965
    assert state.wyckoff_range.low == 1.0965
    assert state.wyckoff_range.high == 1.1100
    assert state.wyckoff_range.tap_count == 3
    assert state.status is TapModelStatus.READY_FOR_ENTRY
    assert state.bos_search_armed is True


def test_tap_three_spacing_cannot_exceed_tap_one_to_two() -> None:
    machine = make_machine()

    machine.process_bar(
        make_candle(
            8,
            high=1.1010,
            low=1.0980,
            close=1.1005,
        )
    )

    state = machine.process_bar(
        make_candle(
            17,
            high=1.1050,
            low=1.1020,
            close=1.1030,
        )
    )

    assert state.status is TapModelStatus.REPULL_REQUIRED


def test_equal_tap_spacing_is_allowed() -> None:
    machine = make_machine()

    machine.process_bar(
        make_candle(
            8,
            high=1.1010,
            low=1.0980,
            close=1.1005,
        )
    )

    state = machine.process_bar(
        make_candle(
            16,
            high=1.0990,
            low=1.0970,
            close=1.0975,
        )
    )

    assert state.status is TapModelStatus.TAP_3_ACTIVE


def test_range_high_reached_between_tap_two_and_three_requires_repull() -> None:
    machine = make_machine()

    machine.process_bar(
        make_candle(
            8,
            high=1.1010,
            low=1.0980,
            close=1.1005,
        )
    )

    state = machine.process_bar(
        make_candle(
            10,
            high=1.1100,
            low=1.1050,
            close=1.1080,
        )
    )

    assert state.status is TapModelStatus.REPULL_REQUIRED


def test_bos_target_inside_range_is_eligible() -> None:
    machine = make_machine()

    assert machine.bos_target_is_inside_range(1.1050)


def test_bos_target_below_range_low_is_not_eligible() -> None:
    machine = make_machine()

    assert not machine.bos_target_is_inside_range(1.0990)


def test_bos_target_at_range_boundary_is_not_eligible() -> None:
    machine = make_machine()

    assert not machine.bos_target_is_inside_range(1.1000)
    assert not machine.bos_target_is_inside_range(1.1100)


def test_spacing_ratio_is_recorded() -> None:
    machine = make_machine()

    machine.process_bar(
        make_candle(
            8,
            high=1.1010,
            low=1.0980,
            close=1.1005,
        )
    )

    machine.process_bar(
        make_candle(
            12,
            high=1.0990,
            low=1.0970,
            close=1.0975,
        )
    )

    state = machine.process_bar(
        make_candle(
            13,
            high=1.1010,
            low=1.0965,
            close=1.0990,
        )
    )

    assert state.spacing is not None
    assert state.spacing.tap_1_to_2_bars == 8
    assert state.spacing.tap_2_to_3_bars == 5
    assert state.spacing.ratio == 0.625
