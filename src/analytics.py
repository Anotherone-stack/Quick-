
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass(frozen=True)
class AnalyticsConfig:
    """Configurable market analytics settings."""
    symbol: str = "BTCUSDT"
    large_trade_threshold: float = 10_000.0
    rolling_window: str = "5min"


class MarketAnalytics:
    """Calculate market statistics independently of the GUI."""

    def __init__(
        self,
        config: Optional[AnalyticsConfig] = None,
    ) -> None:
        self.config = config or AnalyticsConfig()

    @staticmethod
    def _validate_trades(trades: pd.DataFrame) -> pd.DataFrame:
        """Validate and normalize trade data."""
        required = {"price", "quantity"}

        missing = required - set(trades.columns)
        if missing:
            raise ValueError(
                f"Missing required trade columns: {sorted(missing)}"
            )

        result = trades.copy()
        result["price"] = pd.to_numeric(
            result["price"], errors="raise"
        )
        result["quantity"] = pd.to_numeric(
            result["quantity"], errors="raise"
        )

        if (result["price"] < 0).any():
            raise ValueError("Trade prices cannot be negative.")

        if (result["quantity"] < 0).any():
            raise ValueError("Trade quantities cannot be negative.")

        if "timestamp" in result.columns:
            result["timestamp"] = pd.to_datetime(
                result["timestamp"], utc=True, errors="raise"
            )

        result["trade_value"] = (
            result["price"] * result["quantity"]
        )

        return result

    @staticmethod
    def classify_trades(trades: pd.DataFrame) -> pd.DataFrame:
        """
        Estimate trade direction.

        Preferred input:
            is_buyer_maker: True means the buyer was the maker,
            so the trade is classified as an aggressive sell.

        Without that field, use a tick-rule approximation:
            price rises -> buy
            price falls -> sell
            unchanged -> unknown
        """
        result = trades.copy()

        if "is_buyer_maker" in result.columns:
            maker = result["is_buyer_maker"]

            result["trade_side"] = "unknown"
            valid = maker.notna()
            result.loc[valid, "trade_side"] = (
                maker.loc[valid]
                .map({True: "sell", False: "buy"})
            )
            return result

        if "price" not in result.columns:
            raise ValueError(
                "Trade classification requires price data."
            )

        price = pd.to_numeric(result["price"], errors="raise")
        change = price.diff()

        result["trade_side"] = "unknown"
        result.loc[change > 0, "trade_side"] = "buy"
        result.loc[change < 0, "trade_side"] = "sell"

        return result

    def analyze_trades(
        self,
        trades: pd.DataFrame,
    ) -> dict:
        """Return aggregate trade statistics."""
        result = self._validate_trades(trades)
        result = self.classify_trades(result)

        large = (
            result["trade_value"]
            >= self.config.large_trade_threshold
        )

        buy = result["trade_side"].eq("buy")
        sell = result["trade_side"].eq("sell")

        stats = {
            "symbol": self.config.symbol,
            "trade_count": int(len(result)),
            "total_volume": float(result["quantity"].sum()),
            "total_traded_value": float(
                result["trade_value"].sum()
            ),
            "average_trade_size": float(
                result["quantity"].mean()
            ) if len(result) else 0.0,
            "average_trade_value": float(
                result["trade_value"].mean()
            ) if len(result) else 0.0,
            "buy_trade_count": int(buy.sum()),
            "sell_trade_count": int(sell.sum()),
            "unknown_trade_count": int(
                result["trade_side"].eq("unknown").sum()
            ),
            "buy_volume": float(
                result.loc[buy, "quantity"].sum()
            ),
            "sell_volume": float(
                result.loc[sell, "quantity"].sum()
            ),
            "large_trade_count": int(large.sum()),
            "large_trade_volume": float(
                result.loc[large, "quantity"].sum()
            ),
            "large_trade_value": float(
                result.loc[large, "trade_value"].sum()
            ),
        }

        return stats

    def rolling_statistics(
        self,
        trades: pd.DataFrame,
    ) -> pd.DataFrame:
        """Calculate rolling trade statistics by timestamp."""
        result = self._validate_trades(trades)

        if "timestamp" not in result.columns:
            raise ValueError(
                "Rolling statistics require a timestamp column."
            )

        result = self.classify_trades(result)
        result = result.sort_values("timestamp")
        result = result.set_index("timestamp")

        result["trade_count"] = 1
        result["buy_volume"] = result["quantity"].where(
            result["trade_side"].eq("buy"), 0.0
        )
        result["sell_volume"] = result["quantity"].where(
            result["trade_side"].eq("sell"), 0.0
        )
        result["large_trade_count"] = (
            result["trade_value"]
            >= self.config.large_trade_threshold
        ).astype(int)

        window = self.config.rolling_window

        rolling = result[
            [
                "quantity",
                "trade_value",
                "trade_count",
                "buy_volume",
                "sell_volume",
                "large_trade_count",
            ]
        ].rolling(window)

        output = pd.DataFrame(index=result.index)
        output["volume"] = rolling["quantity"].sum()
        output["traded_value"] = rolling["trade_value"].sum()
        output["trade_count"] = rolling["trade_count"].sum()
        output["average_trade_size"] = rolling["quantity"].mean()
        output["buy_volume"] = rolling["buy_volume"].sum()
        output["sell_volume"] = rolling["sell_volume"].sum()
        output["large_trade_count"] = (
            rolling["large_trade_count"].sum()
        )

        return output

    @staticmethod
    def calculate_spread(
        bid: float,
        ask: float,
    ) -> dict:
        """Calculate absolute and relative bid-ask spread."""
        if bid < 0 or ask < 0:
            raise ValueError("Bid and ask cannot be negative.")

        if ask < bid:
            raise ValueError("Ask cannot be lower than bid.")

        spread = ask - bid
        midpoint = (ask + bid) / 2

        return {
            "bid": float(bid),
            "ask": float(ask),
            "spread": float(spread),
            "spread_bps": (
                float(spread / midpoint * 10_000)
                if midpoint > 0 else 0.0
            ),
            "midpoint": float(midpoint),
        }
