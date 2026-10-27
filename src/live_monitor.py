from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from math import isfinite
from threading import RLock
from typing import Any
from zoneinfo import ZoneInfo

from src.config import LARGE_TRADE_SHARES, MAX_TAPE_ROWS, SYMBOL

EASTERN = ZoneInfo("America/New_York")


class LiveMonitor:
    """Keep a thread-safe snapshot of live quotes and recent trades."""

    def __init__(
        self,
        symbol: str = SYMBOL,
        large_trade_shares: int = LARGE_TRADE_SHARES,
        max_tape_rows: int = MAX_TAPE_ROWS,
    ) -> None:
        if not symbol.strip():
            raise ValueError("A symbol is required.")
        if large_trade_shares < 1:
            raise ValueError("large_trade_shares must be positive.")
        if max_tape_rows < 1:
            raise ValueError("max_tape_rows must be positive.")

        self.symbol = symbol.strip().upper()
        self.large_trade_shares = large_trade_shares
        self._quote: dict[str, float | int] | None = None
        self._trades: deque[dict[str, Any]] = deque(maxlen=max_tape_rows)
        self._trade_count = 0
        self._large_trade_count = 0
        self._last_trade_price: float | None = None
        self._lock = RLock()

    @staticmethod
    def _value(event: Any, name: str, default: Any = None) -> Any:
        if isinstance(event, dict):
            return event.get(name, default)
        return getattr(event, name, default)

    def record_quote(self, quote: Any) -> None:
        bid = float(self._value(quote, "bid_price"))
        ask = float(self._value(quote, "ask_price"))
        bid_size = int(self._value(quote, "bid_size"))
        ask_size = int(self._value(quote, "ask_size"))
        if not all(isfinite(price) for price in (bid, ask)):
            raise ValueError("Quote prices must be finite.")
        if bid_size < 0 or ask_size < 0:
            raise ValueError("Quote sizes cannot be negative.")

        with self._lock:
            self._quote = {
                "bid": bid,
                "bid_size": bid_size,
                "ask": ask,
                "ask_size": ask_size,
            }

    def record_trade(self, trade: Any) -> None:
        price = float(self._value(trade, "price"))
        size = int(self._value(trade, "size"))
        if not isfinite(price) or price <= 0:
            raise ValueError("Trade price must be a positive finite number.")
        if size <= 0:
            raise ValueError("Trade size must be positive.")

        timestamp = self._value(trade, "timestamp")
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        elif not isinstance(timestamp, datetime):
            timestamp = datetime.fromisoformat(
                str(timestamp).replace("Z", "+00:00")
            )
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        with self._lock:
            if self._quote is None:
                side = "UNKNOWN"
            elif (
                self._quote["ask"] > 0
                and price >= self._quote["ask"]
            ):
                side = "BUY-INITIATED (EST.)"
            elif (
                self._quote["bid"] > 0
                and price <= self._quote["bid"]
            ):
                side = "SELL-INITIATED (EST.)"
            else:
                side = "MID-SPREAD / UNCERTAIN"

            is_large = size >= self.large_trade_shares
            trade_record = {
                "time": timestamp.astimezone(EASTERN).strftime(
                    "%H:%M:%S.%f"
                )[:-3],
                "symbol": str(
                    self._value(trade, "symbol", self.symbol)
                ).upper(),
                "price": price,
                "size": size,
                "side": side,
                "alert": "<<< LARGE TRADE" if is_large else "",
                "is_large": is_large,
            }
            self._trades.appendleft(trade_record)
            self._trade_count += 1
            if is_large:
                self._large_trade_count += 1
            self._last_trade_price = price

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "quote": dict(self._quote) if self._quote else None,
                "trades": [dict(trade) for trade in self._trades],
                "trade_count": self._trade_count,
                "large_trade_count": self._large_trade_count,
                "last_trade_price": self._last_trade_price,
            }
