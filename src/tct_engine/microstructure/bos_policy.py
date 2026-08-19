from typing import Protocol

from tct_engine.domain.enums import Timeframe
from tct_engine.microstructure.hierarchy import (
    StructureHierarchy,
    StructureLevel,
)


class BosTargetPolicy(Protocol):
    def select_target(
        self,
        hierarchy: StructureHierarchy,
    ) -> StructureLevel | None: ...


class HierarchyAwareBosPolicy:
    """Use the deepest valid, unobstructed hierarchy level."""

    def select_target(
        self,
        hierarchy: StructureHierarchy,
    ) -> StructureLevel | None:
        for level in reversed(hierarchy.levels):
            if not level.obstructed:
                return level

        return None


class AlwaysM1BosPolicy:
    """Use M1 structure whenever M1 exists in the hierarchy."""

    def select_target(
        self,
        hierarchy: StructureHierarchy,
    ) -> StructureLevel | None:
        for level in reversed(hierarchy.levels):
            if level.timeframe is Timeframe.M1:
                return level

        return None
