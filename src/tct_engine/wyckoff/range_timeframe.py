from dataclasses import dataclass

from tct_engine.domain.enums import Timeframe

RANGE_TIMEFRAME_LADDER = (
    Timeframe.M1,
    Timeframe.M3,
    Timeframe.M5,
    Timeframe.M15,
    Timeframe.M30,
    Timeframe.M45,
)


@dataclass(frozen=True, slots=True)
class RangeFormationEvidence:
    """Evidence that the same candidate range is valid on one timeframe."""

    instrument: str
    timeframe: Timeframe

    tap_1_price: float
    range_high: float

    bullish_leg_valid: bool
    bearish_leg_valid: bool
    midpoint_touched: bool

    @property
    def midpoint(self) -> float:
        return (self.tap_1_price + self.range_high) / 2

    @property
    def is_structurally_valid(self) -> bool:
        return self.bullish_leg_valid and self.bearish_leg_valid and self.midpoint_touched


@dataclass(frozen=True, slots=True)
class RangeTimeframeDiscovery:
    instrument: str
    tap_1_price: float
    range_high: float
    timeframe: Timeframe
    evidence: RangeFormationEvidence


class RangeTimeframeFinder:
    """Find the highest contiguous timeframe where a range remains valid."""

    def find(
        self,
        *,
        instrument: str,
        tap_1_price: float,
        evidence_by_timeframe: dict[
            Timeframe,
            RangeFormationEvidence,
        ],
    ) -> RangeTimeframeDiscovery | None:
        highest_valid: RangeFormationEvidence | None = None

        for timeframe in RANGE_TIMEFRAME_LADDER:
            evidence = evidence_by_timeframe.get(timeframe)

            if evidence is None:
                break

            if not self._matches_candidate(
                evidence=evidence,
                instrument=instrument,
                tap_1_price=tap_1_price,
            ):
                break

            if not evidence.is_structurally_valid:
                break

            highest_valid = evidence

        if highest_valid is None:
            return None

        return RangeTimeframeDiscovery(
            instrument=instrument,
            tap_1_price=tap_1_price,
            range_high=highest_valid.range_high,
            timeframe=highest_valid.timeframe,
            evidence=highest_valid,
        )

    @staticmethod
    def _matches_candidate(
        *,
        evidence: RangeFormationEvidence,
        instrument: str,
        tap_1_price: float,
    ) -> bool:
        return evidence.instrument == instrument and evidence.tap_1_price == tap_1_price
