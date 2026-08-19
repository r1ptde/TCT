from dataclasses import dataclass
from enum import Enum, auto

from tct_engine.domain.enums import Timeframe
from tct_engine.microstructure.structural_points import (
    EstablishedStructuralPoint,
    StructuralPointSide,
)
from tct_engine.microstructure.supply_demand import (
    SupplyDemandSide,
    SupplyDemandStatus,
    SupplyDemandZone,
)


class StructureLevelName(Enum):
    LEVEL_1 = auto()
    LEVEL_2 = auto()
    LEVEL_3 = auto()


@dataclass(frozen=True, slots=True)
class StructureLevel:
    name: StructureLevelName
    point: EstablishedStructuralPoint
    timeframe: Timeframe
    obstructed: bool = False


@dataclass(frozen=True, slots=True)
class StructureHierarchy:
    instrument: str
    side: StructuralPointSide
    levels: tuple[StructureLevel, ...]

    @property
    def level_1(self) -> StructureLevel | None:
        return self._get(StructureLevelName.LEVEL_1)

    @property
    def level_2(self) -> StructureLevel | None:
        return self._get(StructureLevelName.LEVEL_2)

    @property
    def level_3(self) -> StructureLevel | None:
        return self._get(StructureLevelName.LEVEL_3)

    def _get(
        self,
        name: StructureLevelName,
    ) -> StructureLevel | None:
        for level in self.levels:
            if level.name is name:
                return level

        return None


TIMEFRAME_LADDER = (
    Timeframe.M15,
    Timeframe.M5,
    Timeframe.M3,
    Timeframe.M1,
)


class StructureHierarchyBuilder:
    """Build up to three distinct structural levels across timeframes."""

    def build(
        self,
        *,
        instrument: str,
        side: StructuralPointSide,
        points_by_timeframe: dict[
            Timeframe,
            EstablishedStructuralPoint,
        ],
        zones: tuple[SupplyDemandZone, ...] = (),
    ) -> StructureHierarchy:
        ordered_points = self._ordered_distinct_points(
            side=side,
            points_by_timeframe=points_by_timeframe,
        )

        levels: list[StructureLevel] = []

        for index, point in enumerate(ordered_points[:3]):
            level_name = (
                StructureLevelName.LEVEL_1,
                StructureLevelName.LEVEL_2,
                StructureLevelName.LEVEL_3,
            )[index]

            obstructed = (
                False
                if index == 0
                else self._is_obstructed(
                    side=side,
                    level_1=ordered_points[0],
                    candidate=point,
                    zones=zones,
                )
            )

            levels.append(
                StructureLevel(
                    name=level_name,
                    point=point,
                    timeframe=point.timeframe,
                    obstructed=obstructed,
                )
            )

        return StructureHierarchy(
            instrument=instrument,
            side=side,
            levels=tuple(levels),
        )

    @staticmethod
    def _ordered_distinct_points(
        *,
        side: StructuralPointSide,
        points_by_timeframe: dict[
            Timeframe,
            EstablishedStructuralPoint,
        ],
    ) -> list[EstablishedStructuralPoint]:
        result: list[EstablishedStructuralPoint] = []

        last_price: float | None = None

        for timeframe in TIMEFRAME_LADDER:
            point = points_by_timeframe.get(timeframe)

            if point is None:
                continue

            if point.side is not side:
                continue

            if last_price is not None and point.price == last_price:
                continue

            result.append(point)
            last_price = point.price

        return result

    @staticmethod
    def _is_obstructed(
        *,
        side: StructuralPointSide,
        level_1: EstablishedStructuralPoint,
        candidate: EstablishedStructuralPoint,
        zones: tuple[SupplyDemandZone, ...],
    ) -> bool:
        low = min(level_1.price, candidate.price)
        high = max(level_1.price, candidate.price)

        relevant_side = (
            SupplyDemandSide.DEMAND if side is StructuralPointSide.LOW else SupplyDemandSide.SUPPLY
        )

        for zone in zones:
            if zone.side is not relevant_side:
                continue

            if zone.status in {
                SupplyDemandStatus.MITIGATED,
                SupplyDemandStatus.INVALIDATED,
            }:
                continue

            overlaps_interval = zone.upper_bound > low and zone.lower_bound < high

            if overlaps_interval:
                return True

        return False
