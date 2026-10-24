#def test_large_trade_threshold():
 #   threshold = 1000

  #  assert 1000 >= threshold
   # assert 999 < threshold


  
import pandas as pd
import pytest

from src.analytics import AnalyticsConfig, MarketAnalytics


@pytest.fixture
def analytics():
    return MarketAnalytics(
        AnalyticsConfig(
            symbol="BTCUSDT",
            large_trade_threshold=1000,
            rolling_window="5min",
        )
    )


@pytest.fixture
def trades():
    return pd.DataFrame({
        "timestamp": pd.to_datetime([
            "2026-10-24T10:00:00Z",
            "2026-10-24T10:01:00Z",
            "2026-10-24T10:02:00Z",
        ]),
        "price": [100, 200, 150],
        "quantity": [5, 5, 2],
    })


def test_large_trade_threshold(analytics):
    threshold = analytics.config.large_trade_threshold

    assert 1000 >= threshold
    assert 999 < threshold


def test_trade_value_and_large_trade_count(analytics, trades):
    stats = analytics.analyze_trades(trades)

    # Values: 500, 1000, 300
    assert stats["large_trade_count"] == 1
    assert stats["large_trade_value"] == 1000
    assert stats["large_trade_volume"] == 5


def test_total_traded_volume(analytics, trades):
    stats = analytics.analyze_trades(trades)

    assert stats["total_volume"] == 12
    assert stats["trade_count"] == 3


def test_average_trade_size(analytics, trades):
    stats = analytics.analyze_trades(trades)

    assert stats["average_trade_size"] == pytest.approx(4)
    assert stats["average_trade_value"] == pytest.approx(
        600
    )


def test_tick_rule_trade_classification(analytics):
    trades = pd.DataFrame({
        "price": [100, 105, 105, 98],
    })

    result = analytics.classify_trades(trades)

    assert result["trade_side"].tolist() == [
        "unknown",
        "buy",
        "unknown",
        "sell",
    ]


def test_buyer_maker_classification(analytics):
    trades = pd.DataFrame({
        "price": [100, 101, 102],
        "is_buyer_maker": [True, False, True],
    })

    result = analytics.classify_trades(trades)

    assert result["trade_side"].tolist() == [
        "sell",
        "buy",
        "sell",
    ]


def test_buy_and_sell_statistics(analytics):
    trades = pd.DataFrame({
        "price": [100, 110, 105],
        "quantity": [2, 3, 4],
        "is_buyer_maker": [False, True, False],
    })

    stats = analytics.analyze_trades(trades)

    assert stats["buy_trade_count"] == 2
    assert stats["sell_trade_count"] == 1
    assert stats["buy_volume"] == 6
    assert stats["sell_volume"] == 3
    assert stats["unknown_trade_count"] == 0


def test_bid_ask_spread(analytics):
    result = analytics.calculate_spread(99, 101)

    assert result["spread"] == 2
    assert result["midpoint"] == 100
    assert result["spread_bps"] == pytest.approx(200)


def test_zero_midpoint_spread(analytics):
    result = analytics.calculate_spread(0, 0)

    assert result["spread"] == 0
    assert result["spread_bps"] == 0


def test_invalid_trade_columns(analytics):
    trades = pd.DataFrame({"price": [100]})

    with pytest.raises(ValueError, match="Missing required"):
        analytics.analyze_trades(trades)


def test_negative_quantity_rejected(analytics):
    trades = pd.DataFrame({
        "price": [100],
        "quantity": [-1],
    })

    with pytest.raises(ValueError, match="quantities"):
        analytics.analyze_trades(trades)


def test_rolling_statistics(analytics, trades):
    result = analytics.rolling_statistics(trades)

    assert result["trade_count"].iloc[-1] == 3
    assert result["volume"].iloc[-1] == 12
    assert result["average_trade_size"].iloc[-1] == 4
 