from tct_engine.domain.enums import Timeframe
from tct_engine.wyckoff.range_timeframe import (
    RangeFormationEvidence,
    RangeTimeframeFinder,
)


def make_evidence(
    *,
    timeframe: Timeframe,
    tap_1_price: float = 1.1000,
    range_high: float = 1.1100,
    bullish_leg_valid: bool = True,
    bearish_leg_valid: bool = True,
    midpoint_touched: bool = True,
) -> RangeFormationEvidence:
    return RangeFormationEvidence(
        instrument="EURUSD",
        timeframe=timeframe,
        tap_1_price=tap_1_price,
        range_high=range_high,
        bullish_leg_valid=bullish_leg_valid,
        bearish_leg_valid=bearish_leg_valid,
        midpoint_touched=midpoint_touched,
    )


def test_finds_highest_contiguously_valid_timeframe() -> None:
    finder = RangeTimeframeFinder()

    result = finder.find(
        instrument="EURUSD",
        tap_1_price=1.1000,
        evidence_by_timeframe={
            Timeframe.M1: make_evidence(timeframe=Timeframe.M1),
            Timeframe.M3: make_evidence(timeframe=Timeframe.M3),
            Timeframe.M5: make_evidence(timeframe=Timeframe.M5),
            Timeframe.M15: make_evidence(timeframe=Timeframe.M15),
        },
    )

    assert result is not None
    assert result.timeframe is Timeframe.M15


def test_discovery_stops_at_first_invalid_timeframe() -> None:
    finder = RangeTimeframeFinder()

    result = finder.find(
        instrument="EURUSD",
        tap_1_price=1.1000,
        evidence_by_timeframe={
            Timeframe.M1: make_evidence(timeframe=Timeframe.M1),
            Timeframe.M3: make_evidence(timeframe=Timeframe.M3),
            Timeframe.M5: make_evidence(
                timeframe=Timeframe.M5,
                bearish_leg_valid=False,
            ),
            Timeframe.M15: make_evidence(timeframe=Timeframe.M15),
        },
    )

    assert result is not None
    assert result.timeframe is Timeframe.M3


def test_higher_timeframe_cannot_become_valid_again_after_gap() -> None:
    finder = RangeTimeframeFinder()

    result = finder.find(
        instrument="EURUSD",
        tap_1_price=1.1000,
        evidence_by_timeframe={
            Timeframe.M1: make_evidence(timeframe=Timeframe.M1),
            Timeframe.M3: make_evidence(timeframe=Timeframe.M3),
            # M5 deliberately missing.
            Timeframe.M15: make_evidence(timeframe=Timeframe.M15),
            Timeframe.M30: make_evidence(timeframe=Timeframe.M30),
        },
    )

    assert result is not None
    assert result.timeframe is Timeframe.M3


def test_both_legs_are_required() -> None:
    finder = RangeTimeframeFinder()

    result = finder.find(
        instrument="EURUSD",
        tap_1_price=1.1000,
        evidence_by_timeframe={
            Timeframe.M1: make_evidence(
                timeframe=Timeframe.M1,
                bullish_leg_valid=True,
                bearish_leg_valid=False,
            ),
        },
    )

    assert result is None


def test_midpoint_touch_is_required() -> None:
    finder = RangeTimeframeFinder()

    result = finder.find(
        instrument="EURUSD",
        tap_1_price=1.1000,
        evidence_by_timeframe={
            Timeframe.M1: make_evidence(
                timeframe=Timeframe.M1,
                midpoint_touched=False,
            ),
        },
    )

    assert result is None


def test_different_tap_one_price_breaks_contiguous_validity() -> None:
    finder = RangeTimeframeFinder()

    result = finder.find(
        instrument="EURUSD",
        tap_1_price=1.1000,
        evidence_by_timeframe={
            Timeframe.M1: make_evidence(
                timeframe=Timeframe.M1,
                tap_1_price=1.1000,
            ),
            Timeframe.M3: make_evidence(
                timeframe=Timeframe.M3,
                tap_1_price=1.1000,
            ),
            Timeframe.M5: make_evidence(
                timeframe=Timeframe.M5,
                tap_1_price=1.0995,
            ),
        },
    )

    assert result is not None
    assert result.timeframe is Timeframe.M3


def test_range_discovery_is_hard_capped_at_m45() -> None:
    finder = RangeTimeframeFinder()

    result = finder.find(
        instrument="EURUSD",
        tap_1_price=1.1000,
        evidence_by_timeframe={
            Timeframe.M1: make_evidence(timeframe=Timeframe.M1),
            Timeframe.M3: make_evidence(timeframe=Timeframe.M3),
            Timeframe.M5: make_evidence(timeframe=Timeframe.M5),
            Timeframe.M15: make_evidence(timeframe=Timeframe.M15),
            Timeframe.M30: make_evidence(timeframe=Timeframe.M30),
            Timeframe.M45: make_evidence(timeframe=Timeframe.M45),
        },
    )

    assert result is not None
    assert result.timeframe is Timeframe.M45


def test_highest_timeframe_evidence_is_preserved() -> None:
    finder = RangeTimeframeFinder()

    result = finder.find(
        instrument="EURUSD",
        tap_1_price=1.1000,
        evidence_by_timeframe={
            Timeframe.M1: make_evidence(
                timeframe=Timeframe.M1,
                range_high=1.1090,
            ),
            Timeframe.M3: make_evidence(
                timeframe=Timeframe.M3,
                range_high=1.1100,
            ),
        },
    )

    assert result is not None
    assert result.timeframe is Timeframe.M3
    assert result.range_high == 1.1100
    assert result.evidence.timeframe is Timeframe.M3


def test_range_formation_midpoint() -> None:
    evidence = make_evidence(
        timeframe=Timeframe.M15,
        tap_1_price=1.1000,
        range_high=1.1100,
    )

    assert evidence.midpoint == 1.1050
