from dataclasses import dataclass

from tct_engine.domain.market_data import Candle, Tick
from tct_engine.events.base import Event
from tct_engine.ingestion.validation import TickRejectionReason


@dataclass(frozen=True, slots=True, kw_only=True)
class TickReceived(Event):
    tick: Tick


@dataclass(frozen=True, slots=True, kw_only=True)
class TickValidated(Event):
    tick: Tick


@dataclass(frozen=True, slots=True, kw_only=True)
class TickRejected(Event):
    tick: Tick
    reason: TickRejectionReason


@dataclass(frozen=True, slots=True, kw_only=True)
class BarOpened(Event):
    candle: Candle


@dataclass(frozen=True, slots=True, kw_only=True)
class BarUpdated(Event):
    candle: Candle


@dataclass(frozen=True, slots=True, kw_only=True)
class BarClosed(Event):
    candle: Candle
