from dataclasses import dataclass
from enum import Enum, auto

from tct_engine.domain.enums import MarketBias, Timeframe
from tct_engine.microstructure.structural_points import (
    EstablishedStructuralPoint,
    StructuralPointSide,
)


class StructureClassification(Enum):
    HH = auto()
    LH = auto()
    EQH = auto()

    HL = auto()
    LL = auto()
    EQL = auto()


@dataclass(frozen=True, slots=True)
class MarketStructureUpdate:
    instrument: str
    timeframe: Timeframe
    point: EstablishedStructuralPoint
    classification: StructureClassification | None
    bias: MarketBias


class MarketStructureClassifier:
    """Classify established structural points and derive market bias."""

    def __init__(self) -> None:
        self._previous_high: dict[
            tuple[str, Timeframe],
            EstablishedStructuralPoint,
        ] = {}

        self._previous_low: dict[
            tuple[str, Timeframe],
            EstablishedStructuralPoint,
        ] = {}

        self._latest_high_classification: dict[
            tuple[str, Timeframe],
            StructureClassification,
        ] = {}

        self._latest_low_classification: dict[
            tuple[str, Timeframe],
            StructureClassification,
        ] = {}

    def process_point(
        self,
        point: EstablishedStructuralPoint,
    ) -> MarketStructureUpdate:
        key = (point.instrument, point.timeframe)

        if point.side is StructuralPointSide.HIGH:
            classification = self._classify_high(key, point)
        else:
            classification = self._classify_low(key, point)

        bias = self._derive_bias(key)

        return MarketStructureUpdate(
            instrument=point.instrument,
            timeframe=point.timeframe,
            point=point,
            classification=classification,
            bias=bias,
        )

    def _classify_high(
        self,
        key: tuple[str, Timeframe],
        point: EstablishedStructuralPoint,
    ) -> StructureClassification | None:
        previous = self._previous_high.get(key)

        self._previous_high[key] = point

        if previous is None:
            return None

        if point.price > previous.price:
            classification = StructureClassification.HH
        elif point.price < previous.price:
            classification = StructureClassification.LH
        else:
            classification = StructureClassification.EQH

        self._latest_high_classification[key] = classification

        return classification

    def _classify_low(
        self,
        key: tuple[str, Timeframe],
        point: EstablishedStructuralPoint,
    ) -> StructureClassification | None:
        previous = self._previous_low.get(key)

        self._previous_low[key] = point

        if previous is None:
            return None

        if point.price > previous.price:
            classification = StructureClassification.HL
        elif point.price < previous.price:
            classification = StructureClassification.LL
        else:
            classification = StructureClassification.EQL

        self._latest_low_classification[key] = classification

        return classification

    def _derive_bias(
        self,
        key: tuple[str, Timeframe],
    ) -> MarketBias:
        high = self._latest_high_classification.get(key)
        low = self._latest_low_classification.get(key)

        if high is StructureClassification.HH and low is StructureClassification.HL:
            return MarketBias.BULLISH

        if high is StructureClassification.LH and low is StructureClassification.LL:
            return MarketBias.BEARISH

        return MarketBias.NEUTRAL
