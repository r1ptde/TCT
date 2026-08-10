from tct_engine.infrastructure.clock import ReplayClock
from tct_engine.ingestion.pipeline import TickIngestionPipeline
from tct_engine.research.replay_source import HistoricalTickSource


class ReplayEngine:
    """Drive historical ticks through the live ingestion path."""

    def __init__(
        self,
        *,
        source: HistoricalTickSource,
        clock: ReplayClock,
        ingestion_pipeline: TickIngestionPipeline,
    ) -> None:
        self._source = source
        self._clock = clock
        self._ingestion_pipeline = ingestion_pipeline

    async def run(self) -> int:
        processed = 0

        async for raw_tick in self._source.stream():
            self._clock.advance_to(raw_tick.timestamp)
            await self._ingestion_pipeline.process(raw_tick)
            processed += 1

        return processed
