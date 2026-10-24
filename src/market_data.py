
# src/market_data.py

from __future__ import annotations

import asyncio
import logging
import os
import random
import threading
import time

from datetime import datetime, timezone
from typing import Any, Callable, Optional

from alpaca.data.enums import DataFeed
from alpaca.data.live import StockDataStream
import logging

logger = logging.getLogger("market_app.market_data")

#logger = logging.getLogger(__name__)

TradeCallback = Callable[[Any], None]
QuoteCallback = Callable[[Any], None]


class AlpacaMarketData:
    """Manage an Alpaca stock market-data stream."""

    def __init__(
        self,
        symbols: list[str],
        on_trade: Optional[TradeCallback] = None,
        on_quote: Optional[QuoteCallback] = None,
        feed: DataFeed = DataFeed.IEX,
        reconnect_initial: float = 1.0,
        reconnect_max: float = 60.0,
        max_reconnect_attempts: Optional[int] = None,
    ) -> None:
        if not symbols:
            raise ValueError("At least one symbol is required.")

        if reconnect_initial <= 0 or reconnect_max < reconnect_initial:
            raise ValueError("Invalid reconnect backoff settings.")

        self.symbols = list(dict.fromkeys(
            symbol.strip().upper() for symbol in symbols
            if symbol.strip()
        ))
        if not self.symbols:
            raise ValueError("At least one valid symbol is required.")

        self.on_trade = on_trade
        self.on_quote = on_quote
        self.feed = feed
        self.reconnect_initial = reconnect_initial
        self.reconnect_max = reconnect_max
        self.max_reconnect_attempts = max_reconnect_attempts

        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._stream: Optional[StockDataStream] = None

        self._running = False
        self._connected = False
        self._last_event_at: Optional[datetime] = None
        self._last_error: Optional[str] = None
        self._reconnect_attempts = 0

        self._api_key = os.getenv("ALPACA_API_KEY")
        self._secret_key = os.getenv("ALPACA_SECRET_KEY")

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._running

    @property
    def is_connected(self) -> bool:
        with self._lock:
            return self._connected

    @property
    def last_event_at(self) -> Optional[datetime]:
        with self._lock:
            return self._last_event_at

    @property
    def last_error(self) -> Optional[str]:
        with self._lock:
            return self._last_error

    @property
    def reconnect_attempts(self) -> int:
        with self._lock:
            return self._reconnect_attempts

    def status(self) -> dict[str, Any]:
        """Return a thread-safe snapshot of connection health."""
        with self._lock:
            last_event = self._last_event_at
            age = (
                (datetime.now(timezone.utc) - last_event).total_seconds()
                if last_event is not None
                else None
            )

            return {
                "running": self._running,
                "connected": self._connected,
                "symbols": list(self.symbols),
                "last_event_at": last_event,
                "seconds_since_last_event": age,
                "last_error": self._last_error,
                "reconnect_attempts": self._reconnect_attempts,
            }

    def start(self) -> None:
        """Start the stream in a background thread."""
        with self._lock:
            if self._thread and self._thread.is_alive():
                return

            if not self._api_key or not self._secret_key:
                raise RuntimeError(
                    "Set ALPACA_API_KEY and ALPACA_SECRET_KEY."
                )

            self._stop_event.clear()
            self._running = True
            self._thread = threading.Thread(
                target=self._run_loop,
                name="alpaca-market-data",
                daemon=True,
            )
            self._thread.start()

    def stop(self, timeout: float = 10.0) -> None:
        """Request shutdown and wait for the worker thread."""
        self._stop_event.set()

        with self._lock:
            stream = self._stream
            thread = self._thread

        if stream is not None:
            try:
                stream.stop()
            except Exception:
                logger.exception("Error stopping Alpaca stream")

        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=timeout)

        with self._lock:
            if thread is None or not thread.is_alive():
                self._running = False
                self._connected = False
                self._stream = None
                self._thread = None
            else:
                logger.warning(
                    "Market-data worker did not stop within %.1f seconds",
                    timeout,
                )

    async def _handle_trade(self, trade: Any) -> None:
        self._mark_event()
        self._dispatch(self.on_trade, trade, "trade")

    async def _handle_quote(self, quote: Any) -> None:
        self._mark_event()
        self._dispatch(self.on_quote, quote, "quote")

    def _mark_event(self) -> None:
        with self._lock:
            self._last_event_at = datetime.now(timezone.utc)

    @staticmethod
    def _dispatch(
        callback: Optional[Callable[[Any], None]],
        event: Any,
        event_name: str,
    ) -> None:
        if callback is None:
            return

        try:
            callback(event)
        except Exception:
            logger.exception(
                "Error in application %s callback", event_name
            )

    def _create_stream(self) -> StockDataStream:
        stream = StockDataStream(
            self._api_key,
            self._secret_key,
            feed=self.feed,
        )

        stream.subscribe_trades(self._handle_trade, *self.symbols)
        stream.subscribe_quotes(self._handle_quote, *self.symbols)

        return stream

    def _run_loop(self) -> None:
        """Run the stream and retry after unexpected exits."""
        consecutive_failures = 0

        try:
            while not self._stop_event.is_set():
                stream = None

                try:
                    stream = self._create_stream()

                    with self._lock:
                        self._stream = stream
                        self._connected = False

                    logger.info(
                        "Starting Alpaca stream for %s",
                        ", ".join(self.symbols),
                    )

                    # StockDataStream.run() blocks until stopped
                    # or the SDK exits with an error.
                    stream.run()

                    if self._stop_event.is_set():
                        break

                    raise ConnectionError(
                        "Alpaca stream exited unexpectedly."
                    )

                except Exception as exc:
                    with self._lock:
                        self._connected = False
                        self._last_error = str(exc)

                    if self._stop_event.is_set():
                        break

                    consecutive_failures += 1

                    with self._lock:
                        self._reconnect_attempts += 1
                        attempt = self._reconnect_attempts

                    if (
                        self.max_reconnect_attempts is not None
                        and consecutive_failures
                        > self.max_reconnect_attempts
                    ):
                        logger.error(
                            "Reconnect limit reached; giving up."
                        )
                        break

                    delay = min(
                        self.reconnect_initial
                        * (2 ** min(consecutive_failures - 1, 20)),
                        self.reconnect_max,
                    )
                    delay *= random.uniform(0.8, 1.2)

                    logger.warning(
                        "Market stream failed (attempt %d): %s. "
                        "Retrying in %.1f seconds.",
                        attempt,
                        exc,
                        delay,
                    )

                    self._stop_event.wait(delay)

                finally:
                    if stream is not None:
                        try:
                            stream.stop()
                        except Exception:
                            logger.debug(
                                "Stream cleanup failed",
                                exc_info=True,
                            )

                    with self._lock:
                        if self._stream is stream:
                            self._stream = None
                        self._connected = False

        finally:
            with self._lock:
                self._running = False
                self._connected = False
                self._stream = None

            logger.info("Alpaca market-data worker stopped.")
