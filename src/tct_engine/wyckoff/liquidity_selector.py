from dataclasses import dataclass
from enum import Enum, auto

from tct_engine.microstructure.market_structure import (
    StructureClassification,
)
from tct_engine.microstructure.structural_points import (
    EstablishedStructuralPoint,
    StructuralPointSide,
)
from tct_engine.wyckoff.models import LiquidityPoint
from tct_engine.wyckoff.range import RangeSide, WyckoffRange
from tct_engine.wyckoff.taps import Tap


class LiquiditySelectionPolicy(Enum):
    FIRST_VALID = auto()
    SKIP_ADJACENT = auto()


@dataclass(frozen=True, slots=True)
class ClassifiedStructuralPoint:
    point: EstablishedStructuralPoint
    classification: StructureClassification


class Model2LiquiditySelector:
    """Select extreme liquidity from the expansion leg after Tap 2."""

    def select(
        self,
        *,
        wyckoff_range: WyckoffRange,
        tap_2: Tap,
        points: tuple[ClassifiedStructuralPoint, ...],
        policy: LiquiditySelectionPolicy = (LiquiditySelectionPolicy.SKIP_ADJACENT),
    ) -> LiquidityPoint | None:
        candidates = self._eligible_points(
            wyckoff_range=wyckoff_range,
            tap_2=tap_2,
            points=points,
        )

        if not candidates:
            return None

        index = 0

        if (
            policy is LiquiditySelectionPolicy.SKIP_ADJACENT
            and len(candidates) >= 2
            and self._is_adjacent_to_tap_2(
                tap_2=tap_2,
                point=candidates[0].point,
            )
        ):
            index = 1

        selected = candidates[index].point

        return LiquidityPoint(
            instrument=selected.instrument,
            timeframe=selected.timeframe,
            price=selected.price,
            structural_point=selected,
        )

    @staticmethod
    def _eligible_points(
        *,
        wyckoff_range: WyckoffRange,
        tap_2: Tap,
        points: tuple[ClassifiedStructuralPoint, ...],
    ) -> list[ClassifiedStructuralPoint]:
        if wyckoff_range.side is RangeSide.ACCUMULATION:
            expected_side = StructuralPointSide.LOW
            expected_classification = StructureClassification.HL
        else:
            expected_side = StructuralPointSide.HIGH
            expected_classification = StructureClassification.LH

        return [
            item
            for item in points
            if (
                item.point.side is expected_side
                and item.classification is expected_classification
                and item.point.extreme_candle.open_time > tap_2.candle.open_time
            )
        ]

    @staticmethod
    def _is_adjacent_to_tap_2(
        *,
        tap_2: Tap,
        point: EstablishedStructuralPoint,
    ) -> bool:
        return point.extreme_candle.open_time == tap_2.candle.close_time


class LiquidityPointStateValidator:
    """Check whether selected liquidity remains unswept."""

    @staticmethod
    def remains_unswept(
        *,
        wyckoff_range: WyckoffRange,
        liquidity_point: LiquidityPoint,
        subsequent_points: tuple[EstablishedStructuralPoint, ...],
    ) -> bool:
        if wyckoff_range.side is RangeSide.ACCUMULATION:
            return all(
                point.price >= liquidity_point.price
                for point in subsequent_points
                if point.side is StructuralPointSide.LOW
            )

        return all(
            point.price <= liquidity_point.price
            for point in subsequent_points
            if point.side is StructuralPointSide.HIGH
        )
