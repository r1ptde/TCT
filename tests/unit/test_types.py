from tct_engine.utils.types import MarketBias, RangeStatus


def test_market_bias_values_are_distinct() -> None:
    assert MarketBias.BULLISH is not MarketBias.BEARISH


def test_range_status_values_are_distinct() -> None:
    assert RangeStatus.ACTIVE is not RangeStatus.INVALIDATED
