from dataclasses import dataclass

from tct_engine.domain.enums import Timeframe
from tct_engine.domain.market_data import Candle
from tct_engine.microstructure.structural_points import (
    EstablishedStructuralPoint,
    StructuralPointSide,
)


@dataclass(frozen=True, slots=True)
class ActiveStructuralExtreme:
    instrument: str
    timeframe: Timeframe
    side: StructuralPointSide
    price: float
    source_point: EstablishedStructuralPoint
    updated_by: Candle


class ActiveStructuralExtremeTracker:
    """Track wick extensions of the currently active structural high/low."""

    def __init__(self) -> None:
        self._active: dict[
            tuple[str, Timeframe, StructuralPointSide],
            ActiveStructuralExtreme,
        ] = {}

    def set_structural_point(
        self,
        point: EstablishedStructuralPoint,
    ) -> ActiveStructuralExtreme:
        key = (
            point.instrument,
            point.timeframe,
            point.side,
        )

        active = ActiveStructuralExtreme(
            instrument=point.instrument,
            timeframe=point.timeframe,
            side=point.side,
            price=point.price,
            source_point=point,
            updated_by=point.extreme_candle,
        )

        self._active[key] = active

        return active

    def process_bar(
        self,
        candle: Candle,
        *,
        side: StructuralPointSide,
    ) -> ActiveStructuralExtreme | None:
        key = (
            candle.instrument,
            candle.timeframe,
            side,
        )

        current = self._active.get(key)

        if current is None:
            return None

        if side is StructuralPointSide.HIGH and candle.high > current.price:
            updated = ActiveStructuralExtreme(
                instrument=current.instrument,
                timeframe=current.timeframe,
                side=current.side,
                price=candle.high,
                source_point=current.source_point,
                updated_by=candle,
            )

            self._active[key] = updated
            return updated

        if side is StructuralPointSide.LOW and candle.low < current.price:
            updated = ActiveStructuralExtreme(
                instrument=current.instrument,
                timeframe=current.timeframe,
                side=current.side,
                price=candle.low,
                source_point=current.source_point,
                updated_by=candle,
            )

            self._active[key] = updated
            return updated

        return current

    def get(
        self,
        *,
        instrument: str,
        timeframe: Timeframe,
        side: StructuralPointSide,
    ) -> ActiveStructuralExtreme | None:
        return self._active.get(
            (
                instrument,
                timeframe,
                side,
            )
        )
