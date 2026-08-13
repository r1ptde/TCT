from dataclasses import dataclass, replace
from enum import Enum, auto

from tct_engine.domain.enums import Timeframe
from tct_engine.domain.market_data import Candle
from tct_engine.microstructure.active_extremes import (
    ActiveStructuralExtremeTracker,
)
from tct_engine.microstructure.bos import (
    BreakDirection,
    BreakOfStructure,
)
from tct_engine.microstructure.legs import (
    LegDirection,
    StructuralLegDetection,
)
from tct_engine.microstructure.structural_points import (
    StructuralPointSide,
)


class SupplyDemandSide(Enum):
    DEMAND = auto()
    SUPPLY = auto()


class SupplyDemandStatus(Enum):
    ACTIVE = auto()
    TOUCHED = auto()
    MITIGATED = auto()
    INVALIDATED = auto()


@dataclass(frozen=True, slots=True)
class SupplyDemandZone:
    instrument: str
    timeframe: Timeframe
    side: SupplyDemandSide
    lower_bound: float
    upper_bound: float
    created_by: BreakOfStructure
    status: SupplyDemandStatus
    touched_by: Candle | None = None
    mitigated_by: StructuralLegDetection | None = None
    invalidated_by: Candle | None = None


class SupplyDemandZoneFactory:
    """Create structural supply/demand zones from valid BOS events."""

    def __init__(
        self,
        *,
        extreme_tracker: ActiveStructuralExtremeTracker,
    ) -> None:
        self._extreme_tracker = extreme_tracker

    def create(
        self,
        bos: BreakOfStructure,
    ) -> SupplyDemandZone | None:
        if bos.direction is BreakDirection.BULLISH:
            return self._create_demand(bos)

        return self._create_supply(bos)

    def _create_demand(
        self,
        bos: BreakOfStructure,
    ) -> SupplyDemandZone | None:
        origin_low = self._extreme_tracker.get(
            instrument=bos.instrument,
            timeframe=bos.timeframe,
            side=StructuralPointSide.LOW,
        )

        if origin_low is None:
            return None

        return SupplyDemandZone(
            instrument=bos.instrument,
            timeframe=bos.timeframe,
            side=SupplyDemandSide.DEMAND,
            lower_bound=origin_low.price,
            upper_bound=bos.broken_extreme.price,
            created_by=bos,
            status=SupplyDemandStatus.ACTIVE,
        )

    def _create_supply(
        self,
        bos: BreakOfStructure,
    ) -> SupplyDemandZone | None:
        origin_high = self._extreme_tracker.get(
            instrument=bos.instrument,
            timeframe=bos.timeframe,
            side=StructuralPointSide.HIGH,
        )

        if origin_high is None:
            return None

        return SupplyDemandZone(
            instrument=bos.instrument,
            timeframe=bos.timeframe,
            side=SupplyDemandSide.SUPPLY,
            lower_bound=bos.broken_extreme.price,
            upper_bound=origin_high.price,
            created_by=bos,
            status=SupplyDemandStatus.ACTIVE,
        )


class SupplyDemandZoneTracker:
    """Track touch, mitigation, and invalidation of structural zones."""

    def __init__(self) -> None:
        self._zones: list[SupplyDemandZone] = []

    @property
    def zones(self) -> tuple[SupplyDemandZone, ...]:
        return tuple(self._zones)

    def add(
        self,
        zone: SupplyDemandZone,
    ) -> None:
        self._zones.append(zone)

    def process_bar(
        self,
        candle: Candle,
    ) -> None:
        for index, zone in enumerate(self._zones):
            if (
                zone.instrument != candle.instrument
                or zone.timeframe is not candle.timeframe
                or zone.status
                in {
                    SupplyDemandStatus.MITIGATED,
                    SupplyDemandStatus.INVALIDATED,
                }
            ):
                continue

            updated = self._process_zone_bar(
                zone=zone,
                candle=candle,
            )

            self._zones[index] = updated

    def process_leg(
        self,
        detection: StructuralLegDetection,
    ) -> None:
        for index, zone in enumerate(self._zones):
            if zone.status is not SupplyDemandStatus.TOUCHED:
                continue

            if (
                zone.instrument != detection.second_candle.instrument
                or zone.timeframe is not detection.second_candle.timeframe
            ):
                continue

            if not self._is_valid_leg_away(
                zone=zone,
                detection=detection,
            ):
                continue

            self._zones[index] = replace(
                zone,
                status=SupplyDemandStatus.MITIGATED,
                mitigated_by=detection,
            )

    @staticmethod
    def _process_zone_bar(
        *,
        zone: SupplyDemandZone,
        candle: Candle,
    ) -> SupplyDemandZone:
        if zone.side is SupplyDemandSide.DEMAND:
            if candle.close < zone.lower_bound:
                return replace(
                    zone,
                    status=SupplyDemandStatus.INVALIDATED,
                    invalidated_by=candle,
                )

        else:
            if candle.close > zone.upper_bound:
                return replace(
                    zone,
                    status=SupplyDemandStatus.INVALIDATED,
                    invalidated_by=candle,
                )

        if zone.status is SupplyDemandStatus.ACTIVE:
            if SupplyDemandZoneTracker._candle_touches_zone(
                candle=candle,
                zone=zone,
            ):
                return replace(
                    zone,
                    status=SupplyDemandStatus.TOUCHED,
                    touched_by=candle,
                )

        return zone

    @staticmethod
    def _candle_touches_zone(
        *,
        candle: Candle,
        zone: SupplyDemandZone,
    ) -> bool:
        return candle.high >= zone.lower_bound and candle.low <= zone.upper_bound

    @staticmethod
    def _is_valid_leg_away(
        *,
        zone: SupplyDemandZone,
        detection: StructuralLegDetection,
    ) -> bool:
        second = detection.second_candle

        if zone.side is SupplyDemandSide.DEMAND:
            return detection.direction is LegDirection.BULLISH and second.close > zone.upper_bound

        return detection.direction is LegDirection.BEARISH and second.close < zone.lower_bound
