
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import median
from threading import RLock
from typing import Any, Optional


@dataclass(frozen=True)
class LargeTradeConfig:
    symbol: str = "AAPL"
    min_trade_value: float = 100_000.0
    min_shares: Optional[float] = None
    history_size: int = 5000
    unusual_size_multiplier: float = 3.0
    baseline_size_window: int = 100
    min_baseline_trades: int = 20


class LargeTradeTracker:
    """Track large trades and unusual trade sizes."""

    def __init__(
        self,
        config: Optional[LargeTradeConfig] = None,
    ) -> None:
        self.config = config or LargeTradeConfig()

        if self.config.min_trade_value < 0:
            raise ValueError("min_trade_value cannot be negative")
        if self.config.min_shares is not None:
            if self.config.min_shares < 0:
                raise ValueError("min_shares cannot be negative")
        if self.config.history_size < 1:
            raise ValueError("history_size must be positive")
        if self.config.unusual_size_multiplier <= 0:
            raise ValueError(
                "unusual_size_multiplier must be positive"
            )
        if self.config.baseline_size_window < 1:
            raise ValueError(
                "baseline_size_window must be positive"
            )
        if self.config.min_baseline_trades < 1:
            raise ValueError(
                "min_baseline_trades must be positive"
            )

        self._lock = RLock()
        self._trades: deque[dict[str, Any]] = deque(
            maxlen=self.config.history_size
        )
        self._large_trades: deque[dict[str, Any]] = deque(
            maxlen=self.config.history_size
        )
        self._recent_sizes: deque[float] = deque(
            maxlen=self.config.baseline_size_window
        )
        self._total_seen = 0
        self._total_large_seen = 0
        self._total_shares_seen = 0.0
        self._total_value_seen = 0.0
        self._total_large_shares_seen = 0.0
        self._total_large_value_seen = 0.0
        self._largest_trade: Optional[dict[str, Any]] = None

    @staticmethod
    def _get(
        trade: Any,
        name: str,
        default: Any = None,
    ) -> Any:
        if isinstance(trade, dict):
            return trade.get(name, default)
        return getattr(trade, name, default)

    def process_trade(self, trade: Any) -> dict[str, Any]:
        """
        Process one trade event.

        Expected fields:
            price, size or quantity, timestamp (optional),
            symbol (optional), and is_buyer_maker (optional).

        For Alpaca stock trades, size is the number of shares.
        """
        symbol = str(
            self._get(trade, "symbol", self.config.symbol)
        ).upper()

        if symbol != self.config.symbol.upper():
            raise ValueError(
                f"Expected {self.config.symbol}, received {symbol}"
            )

        price = float(self._get(trade, "price"))
        raw_size = self._get(trade, "size")
        if raw_size is None:
            raw_size = self._get(trade, "quantity")
        size = float(raw_size)

        if price <= 0 or size <= 0:
            raise ValueError("Price and trade size must be positive")

        timestamp = self._get(trade, "timestamp")
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        elif not isinstance(timestamp, datetime):
            timestamp = datetime.fromisoformat(
                str(timestamp).replace("Z", "+00:00")
            )

        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        value = price * size

        # Prefer an explicit exchange-provided aggressor indicator.
        buyer_maker = self._get(trade, "is_buyer_maker")
        if buyer_maker is None:
            side = "unknown"
        else:
            side = "sell" if bool(buyer_maker) else "buy"

        with self._lock:
            # Compare against earlier trades only. Do not include the
            # current trade in its own unusual-size baseline.
            baseline = (
                median(self._recent_sizes)
                if len(self._recent_sizes)
                >= self.config.min_baseline_trades
                else None
            )

            unusual = (
                baseline is not None
                and size >= baseline
                * self.config.unusual_size_multiplier
            )

            large_by_value = value >= self.config.min_trade_value
            large_by_shares = (
                self.config.min_shares is not None
                and size >= self.config.min_shares
            )
            is_large = large_by_value or large_by_shares

            record = {
                "symbol": symbol,
                "timestamp": timestamp,
                "price": price,
                "shares": size,
                "trade_value": value,
                "side": side,
                "is_large": is_large,
                "baseline_median_shares": baseline,
                "is_unusually_large": unusual,
            }

            self._trades.append(record)
            self._total_seen += 1
            self._total_shares_seen += size
            self._total_value_seen += value

            if is_large:
                self._large_trades.append(record.copy())
                self._total_large_seen += 1
                self._total_large_shares_seen += size
                self._total_large_value_seen += value

            if (
                self._largest_trade is None
                or size > self._largest_trade["shares"]
            ):
                self._largest_trade = record.copy()

            self._recent_sizes.append(size)

            return record.copy()

    def summary(self) -> dict[str, Any]:
        """Return cumulative statistics for the current process."""
        with self._lock:
            largest = (
                self._largest_trade.copy()
                if self._largest_trade is not None
                else None
            )

            return {
                "symbol": self.config.symbol,
                "total_trades": self._total_seen,
                "large_trade_count": self._total_large_seen,
                "large_trade_frequency": (
                    self._total_large_seen / self._total_seen
                    if self._total_seen else 0.0
                ),
                "total_shares": self._total_shares_seen,
                "total_trade_value": self._total_value_seen,
                "large_trade_shares": self._total_large_shares_seen,
                "large_trade_value": self._total_large_value_seen,
                "largest_trade": largest,
                "recent_trades_retained": len(self._trades),
                "large_trades_retained": len(self._large_trades),
                "interpretation_warning": (
                    "Trade size and estimated side do not identify "
                    "institutional participants or their intent."
                ),
            }

    def recent_large_trades(
        self,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Return the most recent retained large trades."""
        if limit < 0:
            raise ValueError("limit cannot be negative")

        with self._lock:
            records = list(self._large_trades)
            return [row.copy() for row in records[-limit:]] if limit else []

    def recent_unusual_trades(
        self,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Return recent retained trades unusually large vs baseline."""
        if limit < 0:
            raise ValueError("limit cannot be negative")

        with self._lock:
            records = [
                row.copy()
                for row in self._trades
                if row["is_unusually_large"]
            ]
            return records[-limit:] if limit else []
