from dataclasses import dataclass
from enum import Enum, auto

from tct_engine.domain.market_data import Tick


class TickRejectionReason(Enum):
    NON_POSITIVE_BID = auto()
    NON_POSITIVE_ASK = auto()
    CROSSED_MARKET = auto()
    OUT_OF_ORDER_TIMESTAMP = auto()
    NON_INCREASING_SEQUENCE = auto()
    DUPLICATE_TICK = auto()


@dataclass(frozen=True, slots=True)
class TickValidationResult:
    reason: TickRejectionReason | None = None

    @property
    def is_valid(self) -> bool:
        return self.reason is None


class TickValidator:
    """Stateful validator for canonical market ticks."""

    def __init__(self) -> None:
        self._last_tick_by_stream: dict[tuple[str, str | None], Tick] = {}

    def validate(self, tick: Tick) -> TickValidationResult:
        if tick.bid <= 0:
            return TickValidationResult(TickRejectionReason.NON_POSITIVE_BID)

        if tick.ask <= 0:
            return TickValidationResult(TickRejectionReason.NON_POSITIVE_ASK)

        if tick.bid > tick.ask:
            return TickValidationResult(TickRejectionReason.CROSSED_MARKET)

        stream_key = (tick.instrument, tick.source)
        previous = self._last_tick_by_stream.get(stream_key)

        if previous is not None:
            result = self._validate_against_previous(previous, tick)

            if not result.is_valid:
                return result

        self._last_tick_by_stream[stream_key] = tick

        return TickValidationResult()

    @staticmethod
    def _validate_against_previous(
        previous: Tick,
        tick: Tick,
    ) -> TickValidationResult:
        if tick == previous:
            return TickValidationResult(TickRejectionReason.DUPLICATE_TICK)

        if tick.timestamp < previous.timestamp:
            return TickValidationResult(TickRejectionReason.OUT_OF_ORDER_TIMESTAMP)

        if (
            previous.sequence is not None
            and tick.sequence is not None
            and tick.sequence <= previous.sequence
        ):
            return TickValidationResult(TickRejectionReason.NON_INCREASING_SEQUENCE)

        return TickValidationResult()
