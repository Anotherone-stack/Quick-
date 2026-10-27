
# Allow type annotations to refer to types defined later.
from __future__ import annotations

# Import deque to store a limited number of recent trades.
from collections import deque

# Import dataclass to define configuration settings.
from dataclasses import dataclass

# Import datetime and timezone to manage timestamps in UTC.
from datetime import datetime, timezone

# Import median to calculate the middle value of trade sizes.
from statistics import median

# Import RLock to protect shared data from concurrent thread access.
from threading import RLock

# Import Any for flexible types and Optional for values that may be None.
from typing import Any, Optional


# Define the configuration settings for the trade tracker.
@dataclass(frozen=True)
class LargeTradeConfig:

    # Set the default stock ticker.
    symbol: str = "AAPL"

    # Set the minimum dollar value for a trade to qualify as large.
    min_trade_value: float = 100_000.0

    # Optionally set the minimum number of shares for a large trade.
    min_shares: Optional[float] = None

    # Set the maximum number of recent trades to retain.
    history_size: int = 5000

    # Set the multiplier used to identify unusually large trades.
    unusual_size_multiplier: float = 3.0

    # Set the number of recent trades used to calculate the baseline.
    baseline_size_window: int = 100

    # Set the minimum number of trades needed before calculating the baseline.
    min_baseline_trades: int = 20


# Define the class that tracks large and unusual trades.
class LargeTradeTracker:

    # Describe the purpose of the tracker.
    """Track large trades and unusual trade sizes."""

    # Initialize the tracker with optional configuration settings.
    def __init__(
        self,
        config: Optional[LargeTradeConfig] = None,
    ) -> None:

        # Use the provided configuration or create default settings.
        self.config = config or LargeTradeConfig()

        # Ensure the minimum trade value is not negative.
        if self.config.min_trade_value < 0:
            raise ValueError("min_trade_value cannot be negative")

        # Validate the optional minimum share threshold.
        if self.config.min_shares is not None:

            # Reject a negative minimum share threshold.
            if self.config.min_shares < 0:
                raise ValueError("min_shares cannot be negative")

        # Ensure the retained history size is positive.
        if self.config.history_size < 1:
            raise ValueError("history_size must be positive")

        # Ensure the unusual-size multiplier is positive.
        if self.config.unusual_size_multiplier <= 0:
            raise ValueError(
                "unusual_size_multiplier must be positive"
            )

        # Ensure the rolling baseline window is positive.
        if self.config.baseline_size_window < 1:
            raise ValueError(
                "baseline_size_window must be positive"
            )

        # Ensure the minimum baseline trade count is positive.
        if self.config.min_baseline_trades < 1:
            raise ValueError(
                "min_baseline_trades must be positive"
            )

        # Create a reentrant lock for safe access to shared data.
        self._lock = RLock()

        # Store recent trades in a queue with a maximum capacity.
        self._trades: deque[dict[str, Any]] = deque(
            maxlen=self.config.history_size
        )

        # Store large trades separately in another bounded queue.
        self._large_trades: deque[dict[str, Any]] = deque(
            maxlen=self.config.history_size
        )

        # Store recent trade sizes for calculating the median baseline.
        self._recent_sizes: deque[float] = deque(
            maxlen=self.config.baseline_size_window
        )

        # Initialize the total number of trades processed.
        self._total_seen = 0

        # Initialize the number of large trades processed.
        self._total_large_seen = 0

        # Initialize the cumulative number of shares traded.
        self._total_shares_seen = 0.0

        # Initialize the cumulative dollar value of all trades.
        self._total_value_seen = 0.0

        # Initialize the cumulative share count for large trades.
        self._total_large_shares_seen = 0.0

        # Initialize the cumulative dollar value of large trades.
        self._total_large_value_seen = 0.0

        # Store the largest trade encountered, or None initially.
        self._largest_trade: Optional[dict[str, Any]] = None

    # Define a helper method to retrieve fields from trades.
    @staticmethod
    def _get(
        trade: Any,  # Accept a dictionary or an object.
        name: str,  # Specify the field to retrieve.
        default: Any = None,  # Specify a fallback value.
    ) -> Any:

        # Check whether the trade is a dictionary.
        if isinstance(trade, dict):

            # Return the requested dictionary value or its default.
            return trade.get(name, default)

        # Otherwise, retrieve the requested object attribute.
        return getattr(trade, name, default)

    # Define the method that processes one trade.
    def process_trade(self, trade: Any) -> dict[str, Any]:

        # Document the expected fields and purpose.
        """
        Process one trade event.

        Expected fields:
            price, size or quantity, timestamp (optional),
            symbol (optional), and is_buyer_maker (optional).

        For Alpaca stock trades, size is the number of shares.
        """

        # Read the ticker symbol, using the configured symbol if absent.
        # Convert it to uppercase for consistent comparisons.
        symbol = str(
            self._get(trade, "symbol", self.config.symbol)
        ).upper()

        # Reject a trade that does not match the configured ticker.
        if symbol != self.config.symbol.upper():
            raise ValueError(
                f"Expected {self.config.symbol}, received {symbol}"
            )

        # Retrieve the trade price and convert it to a float.
        price = float(self._get(trade, "price"))

        # First try to retrieve the trade size.
        raw_size = self._get(trade, "size")

        # If size is missing, try the quantity field instead.
        if raw_size is None:
            raw_size = self._get(trade, "quantity")

        # Convert the trade size to a floating-point number.
        size = float(raw_size)

        # Reject trades with non-positive prices or sizes.
        if price <= 0 or size <= 0:
            raise ValueError("Price and trade size must be positive")

        # Retrieve the trade timestamp if one is available.
        timestamp = self._get(trade, "timestamp")

        # Use the current UTC time when the timestamp is missing.
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        # Parse the timestamp if it is not already a datetime object.
        elif not isinstance(timestamp, datetime):
            timestamp = datetime.fromisoformat(
                str(timestamp).replace("Z", "+00:00")
            )

        # Check whether the timestamp has timezone information.
        if timestamp.tzinfo is None:

            # Treat a timezone-naive timestamp as UTC.
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        # Calculate the approximate total dollar value of the trade.
        value = price * size

        # Prefer the exchange-provided buyer-maker indicator.
        buyer_maker = self._get(trade, "is_buyer_maker")

        # Mark the side as unknown when the indicator is missing.
        if buyer_maker is None:
            side = "unknown"

        # Infer the trade direction when the indicator is available.
        else:

            # A buyer who is the maker indicates a sell aggressor.
            # Otherwise, classify the trade as a buy aggressor.
            side = "sell" if bool(buyer_maker) else "buy"

        # Lock shared state before updating trade history and statistics.
        with self._lock:

            # Calculate the median of previous trade sizes when enough
            # historical samples are available.
            # The current trade is deliberately excluded from the baseline.
            baseline = (
                median(self._recent_sizes)
                if len(self._recent_sizes)
                >= self.config.min_baseline_trades
                else None
            )

            # Identify an unusually large trade by comparing its size
            # against the historical median and configured multiplier.
            unusual = (
                baseline is not None
                and size >= baseline
                * self.config.unusual_size_multiplier
            )

            # Check whether the trade meets the dollar-value threshold.
            large_by_value = value >= self.config.min_trade_value

            # Check whether the optional share-count threshold is enabled
            # and the trade meets that threshold.
            large_by_shares = (
                self.config.min_shares is not None
                and size >= self.config.min_shares
            )

            # Classify the trade as large if either threshold is met.
            is_large = large_by_value or large_by_shares

            # Build a dictionary containing the processed trade information.
            record = {
                "symbol": symbol,  # Store the ticker symbol.
                "timestamp": timestamp,  # Store the trade timestamp.
                "price": price,  # Store the price per share.
                "shares": size,  # Store the number of shares traded.
                "trade_value": value,  # Store the estimated trade value.
                "side": side,  # Store the inferred or unknown trade side.
                "is_large": is_large,  # Record whether the trade is large.
                "baseline_median_shares": baseline,  # Store the baseline median.
                "is_unusually_large": unusual,  # Record the unusual-size result.
            }

            # Add the trade to the recent-trades queue.
            self._trades.append(record)

            # Increment the total number of trades processed.
            self._total_seen += 1

            # Add the trade size to the cumulative share count.
            self._total_shares_seen += size

            # Add the trade value to the cumulative dollar total.
            self._total_value_seen += value

            # Process additional statistics when the trade is large.
            if is_large:

                # Store a copy of the large trade in the large-trades queue.
                self._large_trades.append(record.copy())

                # Increment the large-trade count.
                self._total_large_seen += 1

                # Update the cumulative shares in large trades.
                self._total_large_shares_seen += size

                # Update the cumulative value of large trades.
                self._total_large_value_seen += value

            # Check whether this is the first trade or the largest trade so far.
            if (
                self._largest_trade is None
                or size > self._largest_trade["shares"]
            ):

                # Save a copy of the largest trade encountered.
                self._largest_trade = record.copy()

            # Add the current trade size to the rolling baseline history.
            # The oldest size is discarded automatically when the queue is full.
            self._recent_sizes.append(size)

            # Return a copy of the processed trade record.
            return record.copy()

    # Define a method that returns cumulative tracker statistics.
    def summary(self) -> dict[str, Any]:

        # Document the purpose of the summary method.
        """Return cumulative statistics for the current process."""

        # Lock the tracker while reading shared statistics.
        with self._lock:

            # Copy the largest-trade record if one exists.
            # Otherwise, use None.
            largest = (
                self._largest_trade.copy()
                if self._largest_trade is not None
                else None
            )

            # Return the cumulative statistics as a dictionary.
            return {
                "symbol": self.config.symbol,  # Report the configured ticker.
                "total_trades": self._total_seen,  # Report all trades processed.
                "large_trade_count": self._total_large_seen,  # Report large trades processed.

                # Calculate the proportion of processed trades classified as large.
                # Return zero when no trades have been processed.
                "large_trade_frequency": (
                    self._total_large_seen / self._total_seen
                    if self._total_seen else 0.0
                ),

                "total_shares": self._total_shares_seen,  # Report cumulative shares.
                "total_trade_value": self._total_value_seen,  # Report total trade value.
                "large_trade_shares": self._total_large_shares_seen,  # Report large-trade shares.
                "large_trade_value": self._total_large_value_seen,  # Report large-trade value.
                "largest_trade": largest,  # Include the largest trade record.
                "recent_trades_retained": len(self._trades),  # Report retained recent trades.
                "large_trades_retained": len(self._large_trades),  # Report retained large trades.

                # Explain an important limitation of trade-size analysis.
                "interpretation_warning": (
                    "Trade size and estimated side do not identify "
                    "institutional participants or their intent."
                ),
            }

    # Define a method to retrieve the most recent large trades.
    def recent_large_trades(
        self,
        limit: int = 100,  # Set the maximum number of records to return.
    ) -> list[dict[str, Any]]:

        # Document the method's purpose.
        """Return the most recent retained large trades."""

        # Reject negative limits.
        if limit < 0:
            raise ValueError("limit cannot be negative")

        # Lock the tracker while reading the large-trades queue.
        with self._lock:

            # Convert the queue into a regular list.
            records = list(self._large_trades)

            # Return copies of the most recent requested records.
            # Return an empty list when the limit is zero.
            return [row.copy() for row in records[-limit:]] if limit else []

    # Define a method to retrieve the most recent unusual trades.
    def recent_unusual_trades(
        self,
        limit: int = 100,  # Set the maximum number of records to return.
    ) -> list[dict[str, Any]]:

        # Document the method's purpose.
        """Return recent retained trades unusually large vs baseline."""

        # Reject negative limits.
        if limit < 0:
            raise ValueError("limit cannot be negative")

        # Lock the tracker while reading recent trade records.
        with self._lock:

            # Select copies of the trades marked as unusually large.
            records = [
                row.copy()
                for row in self._trades
                if row["is_unusually_large"]
            ]

            # Return the most recent requested unusual trades.
            # Return an empty list when the limit is zero.
            return records[-limit:] if limit else []
