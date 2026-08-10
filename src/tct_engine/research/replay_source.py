from collections.abc import AsyncIterator, Iterable

from tct_engine.ingestion.models import RawTick


class HistoricalTickSource:
    """Deterministic historical tick source."""

    def __init__(self, ticks: Iterable[RawTick]) -> None:
        self._ticks = tuple(
            sorted(
                ticks,
                key=lambda tick: (
                    tick.timestamp,
                    tick.sequence if tick.sequence is not None else -1,
                ),
            )
        )

    async def stream(self) -> AsyncIterator[RawTick]:
        for tick in self._ticks:
            yield tick
