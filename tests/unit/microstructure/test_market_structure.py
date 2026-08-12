from datetime import UTC, datetime, timedelta

from tct_engine.domain.enums import MarketBias, Timeframe
from tct_engine.domain.market_data import Candle
from tct_engine.microstructure.market_structure import (
    MarketStructureClassifier,
    StructureClassification,
)
from tct_engine.microstructure.structural_points import (
    EstablishedStructuralPoint,
    StructuralPointSide,
)


def make_point(
    index: int,
    *,
    side: StructuralPointSide,
    price: float,
) -> EstablishedStructuralPoint:
    open_time = datetime(
        2026,
        8,
        12,
        8,
        0,
        tzinfo=UTC,
    ) + timedelta(minutes=index)

    candle = Candle(
        instrument="EURUSD",
        timeframe=Timeframe.M1,
        open_time=open_time,
        close_time=open_time + timedelta(minutes=1),
        open=price,
        high=price,
        low=price,
        close=price,
        tick_volume=10,
        is_closed=True,
    )

    return EstablishedStructuralPoint(
        instrument="EURUSD",
        timeframe=Timeframe.M1,
        side=side,
        price=price,
        extreme_candle=candle,
        established_by=candle,
    )


def test_first_high_is_unclassified() -> None:
    classifier = MarketStructureClassifier()

    update = classifier.process_point(
        make_point(
            0,
            side=StructuralPointSide.HIGH,
            price=1.1050,
        )
    )

    assert update.classification is None
    assert update.bias is MarketBias.NEUTRAL


def test_first_low_is_unclassified() -> None:
    classifier = MarketStructureClassifier()

    update = classifier.process_point(
        make_point(
            0,
            side=StructuralPointSide.LOW,
            price=1.0950,
        )
    )

    assert update.classification is None
    assert update.bias is MarketBias.NEUTRAL


def test_higher_high_is_classified() -> None:
    classifier = MarketStructureClassifier()

    classifier.process_point(
        make_point(
            0,
            side=StructuralPointSide.HIGH,
            price=1.1050,
        )
    )

    update = classifier.process_point(
        make_point(
            1,
            side=StructuralPointSide.HIGH,
            price=1.1100,
        )
    )

    assert update.classification is StructureClassification.HH


def test_lower_high_is_classified() -> None:
    classifier = MarketStructureClassifier()

    classifier.process_point(
        make_point(
            0,
            side=StructuralPointSide.HIGH,
            price=1.1100,
        )
    )

    update = classifier.process_point(
        make_point(
            1,
            side=StructuralPointSide.HIGH,
            price=1.1050,
        )
    )

    assert update.classification is StructureClassification.LH


def test_equal_high_is_classified() -> None:
    classifier = MarketStructureClassifier()

    classifier.process_point(
        make_point(
            0,
            side=StructuralPointSide.HIGH,
            price=1.1050,
        )
    )

    update = classifier.process_point(
        make_point(
            1,
            side=StructuralPointSide.HIGH,
            price=1.1050,
        )
    )

    assert update.classification is StructureClassification.EQH


def test_higher_low_is_classified() -> None:
    classifier = MarketStructureClassifier()

    classifier.process_point(
        make_point(
            0,
            side=StructuralPointSide.LOW,
            price=1.0950,
        )
    )

    update = classifier.process_point(
        make_point(
            1,
            side=StructuralPointSide.LOW,
            price=1.1000,
        )
    )

    assert update.classification is StructureClassification.HL


def test_lower_low_is_classified() -> None:
    classifier = MarketStructureClassifier()

    classifier.process_point(
        make_point(
            0,
            side=StructuralPointSide.LOW,
            price=1.1000,
        )
    )

    update = classifier.process_point(
        make_point(
            1,
            side=StructuralPointSide.LOW,
            price=1.0950,
        )
    )

    assert update.classification is StructureClassification.LL


def test_equal_low_is_classified() -> None:
    classifier = MarketStructureClassifier()

    classifier.process_point(
        make_point(
            0,
            side=StructuralPointSide.LOW,
            price=1.0950,
        )
    )

    update = classifier.process_point(
        make_point(
            1,
            side=StructuralPointSide.LOW,
            price=1.0950,
        )
    )

    assert update.classification is StructureClassification.EQL


def test_hh_and_hl_produce_bullish_bias() -> None:
    classifier = MarketStructureClassifier()

    classifier.process_point(
        make_point(
            0,
            side=StructuralPointSide.HIGH,
            price=1.1050,
        )
    )

    classifier.process_point(
        make_point(
            1,
            side=StructuralPointSide.LOW,
            price=1.0950,
        )
    )

    hh = classifier.process_point(
        make_point(
            2,
            side=StructuralPointSide.HIGH,
            price=1.1100,
        )
    )

    assert hh.classification is StructureClassification.HH
    assert hh.bias is MarketBias.NEUTRAL

    hl = classifier.process_point(
        make_point(
            3,
            side=StructuralPointSide.LOW,
            price=1.1000,
        )
    )

    assert hl.classification is StructureClassification.HL
    assert hl.bias is MarketBias.BULLISH


def test_lh_and_ll_produce_bearish_bias() -> None:
    classifier = MarketStructureClassifier()

    classifier.process_point(
        make_point(
            0,
            side=StructuralPointSide.HIGH,
            price=1.1100,
        )
    )

    classifier.process_point(
        make_point(
            1,
            side=StructuralPointSide.LOW,
            price=1.1000,
        )
    )

    classifier.process_point(
        make_point(
            2,
            side=StructuralPointSide.HIGH,
            price=1.1050,
        )
    )

    update = classifier.process_point(
        make_point(
            3,
            side=StructuralPointSide.LOW,
            price=1.0950,
        )
    )

    assert update.classification is StructureClassification.LL
    assert update.bias is MarketBias.BEARISH


def test_conflicting_structure_is_neutral() -> None:
    classifier = MarketStructureClassifier()

    classifier.process_point(
        make_point(
            0,
            side=StructuralPointSide.HIGH,
            price=1.1050,
        )
    )

    classifier.process_point(
        make_point(
            1,
            side=StructuralPointSide.LOW,
            price=1.1000,
        )
    )

    classifier.process_point(
        make_point(
            2,
            side=StructuralPointSide.HIGH,
            price=1.1100,
        )
    )

    update = classifier.process_point(
        make_point(
            3,
            side=StructuralPointSide.LOW,
            price=1.0950,
        )
    )

    assert update.classification is StructureClassification.LL
    assert update.bias is MarketBias.NEUTRAL


def test_equal_structure_does_not_create_directional_bias() -> None:
    classifier = MarketStructureClassifier()

    classifier.process_point(
        make_point(
            0,
            side=StructuralPointSide.HIGH,
            price=1.1050,
        )
    )

    classifier.process_point(
        make_point(
            1,
            side=StructuralPointSide.LOW,
            price=1.0950,
        )
    )

    classifier.process_point(
        make_point(
            2,
            side=StructuralPointSide.HIGH,
            price=1.1050,
        )
    )

    update = classifier.process_point(
        make_point(
            3,
            side=StructuralPointSide.LOW,
            price=1.1000,
        )
    )

    assert update.classification is StructureClassification.HL
    assert update.bias is MarketBias.NEUTRAL
