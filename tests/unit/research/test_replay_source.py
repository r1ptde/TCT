from datetime import UTC, datetime, timedelta

import pytest

from tct_engine.ingestion.models import RawTick
from tct_engine.research.replay_source import HistoricalTickSource


@pytest.mark.asyncio
async def test_historical_source_streams_ticks_in_order() -> None:
    start = datetime(2026, 8, 10, 8, 0, tzinfo=UTC)

    later = RawTick(
        instrument="EURUSD",
        timestamp=start + timedelta(seconds=1),
        bid=1.1501,
        ask=1.1503,
        sequence=2,
    )

    earlier = RawTick(
        instrument="EURUSD",
        timestamp=start,
        bid=1.1500,
        ask=1.1502,
        sequence=1,
    )

    source = HistoricalTickSource([later, earlier])

    observed = [tick async for tick in source.stream()]

    assert observed == [earlier, later]
