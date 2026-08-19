from dataclasses import dataclass, replace
from enum import Enum, auto

from tct_engine.domain.enums import Timeframe
from tct_engine.domain.market_data import Candle


class RangeSide(Enum):
    ACCUMULATION = auto()
    DISTRIBUTION = auto()


class RangeStatus(Enum):
    FORMING = auto()
    ACTIVE = auto()
    INVALIDATED = auto()


class DeviationStatus(Enum):
    IN_PROGRESS = auto()
    COMPLETED = auto()
    INVALIDATED = auto()


@dataclass(frozen=True, slots=True)
class WyckoffRange:
    instrument: str
    timeframe: Timeframe
    side: RangeSide
    high: float
    low: float
    tap_count: int
    status: RangeStatus

    @property
    def midpoint(self) -> float:
        return (self.high + self.low) / 2


@dataclass(frozen=True, slots=True)
class Deviation:
    side: RangeSide
    original_boundary: float
    extreme: float
    outside_closes: int
    status: DeviationStatus
    started_by: Candle
    completed_by: Candle | None = None
    invalidated_by: Candle | None = None


class DeviationTracker:
    MAX_OUTSIDE_CLOSES = 3

    def __init__(
        self,
        *,
        wyckoff_range: WyckoffRange,
        lower_limit: float,
        upper_limit: float,
    ) -> None:
        self._range = wyckoff_range
        self._lower_limit = lower_limit
        self._upper_limit = upper_limit
        self._deviation: Deviation | None = None

    @property
    def deviation(self) -> Deviation | None:
        return self._deviation

    def process_bar(
        self,
        candle: Candle,
    ) -> Deviation | None:
        if not candle.is_closed:
            raise ValueError("Deviation detection requires a closed candle.")

        if self._deviation is None:
            self._try_start(candle)
            return self._deviation

        if self._deviation.status is not DeviationStatus.IN_PROGRESS:
            return self._deviation

        self._update(candle)
        return self._deviation

    def _try_start(self, candle: Candle) -> None:
        if self._range.side is RangeSide.ACCUMULATION:
            if candle.low >= self._range.low:
                return

            self._deviation = Deviation(
                side=self._range.side,
                original_boundary=self._range.low,
                extreme=candle.low,
                outside_closes=0 if candle.close >= self._range.low else 1,
                status=(
                    DeviationStatus.COMPLETED
                    if candle.close >= self._range.low
                    else DeviationStatus.IN_PROGRESS
                ),
                started_by=candle,
                completed_by=(candle if candle.close >= self._range.low else None),
            )
            self._validate_limit(candle)
            return

        if candle.high <= self._range.high:
            return

        self._deviation = Deviation(
            side=self._range.side,
            original_boundary=self._range.high,
            extreme=candle.high,
            outside_closes=0 if candle.close <= self._range.high else 1,
            status=(
                DeviationStatus.COMPLETED
                if candle.close <= self._range.high
                else DeviationStatus.IN_PROGRESS
            ),
            started_by=candle,
            completed_by=(candle if candle.close <= self._range.high else None),
        )
        self._validate_limit(candle)

    def _update(self, candle: Candle) -> None:
        assert self._deviation is not None

        deviation = self._deviation

        if deviation.side is RangeSide.ACCUMULATION:
            extreme = min(deviation.extreme, candle.low)

            if candle.close >= deviation.original_boundary:
                self._deviation = replace(
                    deviation,
                    extreme=extreme,
                    status=DeviationStatus.COMPLETED,
                    completed_by=candle,
                )
                return

            outside_closes = deviation.outside_closes + 1

        else:
            extreme = max(deviation.extreme, candle.high)

            if candle.close <= deviation.original_boundary:
                self._deviation = replace(
                    deviation,
                    extreme=extreme,
                    status=DeviationStatus.COMPLETED,
                    completed_by=candle,
                )
                return

            outside_closes = deviation.outside_closes + 1

        self._deviation = replace(
            deviation,
            extreme=extreme,
            outside_closes=outside_closes,
        )

        if outside_closes > self.MAX_OUTSIDE_CLOSES:
            self._deviation = replace(
                self._deviation,
                status=DeviationStatus.INVALIDATED,
                invalidated_by=candle,
            )
            return

        self._validate_limit(candle)

    def _validate_limit(self, candle: Candle) -> None:
        assert self._deviation is not None

        if self._deviation.side is RangeSide.ACCUMULATION:
            breached = candle.close < self._lower_limit
        else:
            breached = candle.close > self._upper_limit

        if breached:
            self._deviation = replace(
                self._deviation,
                status=DeviationStatus.INVALIDATED,
                invalidated_by=candle,
            )
