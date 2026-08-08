from dataclasses import replace
from datetime import datetime, timedelta

from tct_engine.domain.enums import Timeframe
from tct_engine.domain.market_data import Candle, Tick


class BarAggregator:
    """Incrementally aggregate validated ticks into OHLC bars."""

    def __init__(self, timeframe: Timeframe) -> None:
        self._timeframe = timeframe
        self._active_bars: dict[str, Candle] = {}

    @property
    def timeframe(self) -> Timeframe:
        return self._timeframe

    def process_tick(self, tick: Tick) -> tuple[Candle | None, Candle]:
        active = self._active_bars.get(tick.instrument)

        bar_open = self._floor_timestamp(
            tick.timestamp,
            self._timeframe.seconds,
        )

        bar_close = bar_open + timedelta(seconds=self._timeframe.seconds)

        if active is None:
            new_bar = self._new_bar(
                tick=tick,
                open_time=bar_open,
                close_time=bar_close,
            )

            self._active_bars[tick.instrument] = new_bar
            return None, new_bar

        if tick.timestamp < active.close_time:
            updated = replace(
                active,
                high=max(active.high, tick.mid),
                low=min(active.low, tick.mid),
                close=tick.mid,
                tick_volume=active.tick_volume + 1,
            )

            self._active_bars[tick.instrument] = updated
            return None, updated

        closed = replace(active, is_closed=True)

        new_bar = self._new_bar(
            tick=tick,
            open_time=bar_open,
            close_time=bar_close,
        )

        self._active_bars[tick.instrument] = new_bar

        return closed, new_bar

    def _new_bar(
        self,
        *,
        tick: Tick,
        open_time: datetime,
        close_time: datetime,
    ) -> Candle:
        price = tick.mid

        return Candle(
            instrument=tick.instrument,
            timeframe=self._timeframe,
            open_time=open_time,
            close_time=close_time,
            open=price,
            high=price,
            low=price,
            close=price,
            tick_volume=1,
            is_closed=False,
        )

    @staticmethod
    def _floor_timestamp(
        timestamp: datetime,
        interval_seconds: int,
    ) -> datetime:
        epoch_seconds = int(timestamp.timestamp())
        floored_seconds = epoch_seconds - (epoch_seconds % interval_seconds)

        return datetime.fromtimestamp(
            floored_seconds,
            tz=timestamp.tzinfo,
        )
