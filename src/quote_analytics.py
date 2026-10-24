
# src/quote_analytics.py

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from math import isfinite
from typing import Optional


@dataclass(frozen=True)
class Quote:
    bid: Optional[float]
    ask: Optional[float]
    timestamp: float  # Unix timestamp in seconds


@dataclass
class QuoteAnalytics:
    stale_after: float = 30.0
    window_seconds: float = 60.0
    history: deque = field(default_factory=deque)

    def calculate(
        self, quote: Quote, now: Optional[float] = None
    ) -> dict:
        now = (
            datetime.now(timezone.utc).timestamp()
            if now is None else now
        )
        warnings = []
        status = "healthy"

        def valid_price(value):
            return (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and isfinite(value)
                and value > 0
            )

        valid_timestamp = (
            isinstance(quote.timestamp, (int, float))
            and not isinstance(quote.timestamp, bool)
            and isfinite(quote.timestamp)
            and quote.timestamp > 0
            and quote.timestamp <= now
        )

        if not valid_price(quote.bid):
            warnings.append("invalid_bid")
        if not valid_price(quote.ask):
            warnings.append("invalid_ask")
        if not valid_timestamp:
            warnings.append("invalid_timestamp")

        bid_valid = valid_price(quote.bid)
        ask_valid = valid_price(quote.ask)

        spread = midpoint = spread_bps = None
        quote_status = "invalid"

        if bid_valid and ask_valid and valid_timestamp:
            if quote.bid > quote.ask:
                quote_status = "crossed"
                warnings.append("crossed_market")
            elif quote.bid == quote.ask:
                quote_status = "locked"
                spread = 0.0
                warnings.append("locked_market")
            else:
                quote_status = "healthy"
                spread = quote.ask - quote.bid
                midpoint = (quote.bid + quote.ask) / 2
                spread_bps = spread / midpoint * 10_000

        age = now - quote.timestamp if valid_timestamp else None

        if age is not None and age > self.stale_after:
            warnings.append("stale_quote")

        # Count distinct quote updates, not repeated polling snapshots.
        # A changed bid/ask pair is an update; identical pairs are not.
        if valid_timestamp and bid_valid and ask_valid:
            pair = (quote.bid, quote.ask)
            if not self.history or self.history[-1][1] != pair:
                self.history.append((quote.timestamp, pair))

        cutoff = now - self.window_seconds
        while self.history and self.history[0][0] < cutoff:
            self.history.popleft()

        update_count = len(self.history)
        update_frequency = (
            (update_count - 1) / self.window_seconds
            if self.window_seconds > 0 and update_count > 1
            else 0.0
        )

        if warnings:
            status = "warning"

        return {
            "status": status,
            "quote_status": quote_status,
            "bid": quote.bid if bid_valid else None,
            "ask": quote.ask if ask_valid else None,
            "spread": spread,
            "midpoint": midpoint,
            "spread_bps": spread_bps,
            "quote_age_seconds": age,
            "stale": age is None or age > self.stale_after,
            "update_count": update_count,
            "update_frequency_per_second": update_frequency,
            "warnings": warnings,
        }
