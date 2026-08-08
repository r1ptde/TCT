from dataclasses import dataclass

from tct_engine.domain.market_data import Candle, Tick
from tct_engine.events.base import Event


@dataclass(frozen=True, slots=True, kw_only=True)
class TickReceived(Event):
    tick: Tick


@dataclass(frozen=True, slots=True, kw_only=True)
class TickValidated(Event):
    tick: Tick


@dataclass(frozen=True, slots=True, kw_only=True)
class BarClosed(Event):
    candle: Candle
