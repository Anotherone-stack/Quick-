
# Enables postponed evaluation of type annotations, which helps with type hints.
from __future__ import annotations

# Imports the dataclass decorator for automatically creating class methods.
from dataclasses import dataclass

# Imports Optional, which indicates that a value can be a specified type or None.
from typing import Optional

# Imports Pandas for working with tabular data and performing data analysis.
import pandas as pd


# Converts the following class into a dataclass with generated methods.
@dataclass(frozen=True)
# Defines the configuration class for market analytics.
class AnalyticsConfig:
    """Configurable market analytics settings."""

    # Sets the default trading symbol to Bitcoin against Tether.
    symbol: str = "BTCUSDT"

    # Sets the minimum dollar value for a trade to be considered large.
    large_trade_threshold: float = 10_000.0

    # Sets the time interval used for rolling statistics to five minutes.
    rolling_window: str = "5min"


# Defines the class responsible for calculating market statistics.
class MarketAnalytics:
    """Calculate market statistics independently of the GUI."""

    # Initializes a new MarketAnalytics object.
    def __init__(
        # Accepts an optional configuration object.
        self,
        config: Optional[AnalyticsConfig] = None,
    ) -> None:
        # Uses the supplied configuration or creates the default configuration.
        self.config = config or AnalyticsConfig()

    # Defines a static method that does not require a class instance.
    @staticmethod
    # Defines a method that validates and normalizes trade data.
    def _validate_trades(trades: pd.DataFrame) -> pd.DataFrame:
        """Validate and normalize trade data."""

        # Defines the columns that must exist in the trade DataFrame.
        required = {"price", "quantity"}

        # Finds required columns that are missing from the input DataFrame.
        missing = required - set(trades.columns)

        # Checks whether any required columns are missing.
        if missing:
            # Raises an error and lists the missing column names.
            raise ValueError(
                f"Missing required trade columns: {sorted(missing)}"
            )

        # Creates a copy so the original DataFrame is not modified.
        result = trades.copy()

        # Converts price values to numeric values or raises an error.
        result["price"] = pd.to_numeric(
            result["price"], errors="raise"
        )

        # Converts quantity values to numeric values or raises an error.
        result["quantity"] = pd.to_numeric(
            result["quantity"], errors="raise"
        )

        # Checks whether any trade price is below zero.
        if (result["price"] < 0).any():
            # Raises an error if a negative trade price is found.
            raise ValueError("Trade prices cannot be negative.")

        # Checks whether any trade quantity is below zero.
        if (result["quantity"] < 0).any():
            # Raises an error if a negative trade quantity is found.
            raise ValueError("Trade quantities cannot be negative.")

        # Checks whether the DataFrame contains a timestamp column.
        if "timestamp" in result.columns:
            # Converts timestamps to UTC datetime values and rejects invalid ones.
            result["timestamp"] = pd.to_datetime(
                result["timestamp"], utc=True, errors="raise"
            )

        # Calculates each trade's monetary value as price multiplied by quantity.
        result["trade_value"] = (
            result["price"] * result["quantity"]
        )

        # Returns the validated DataFrame with its calculated trade values.
        return result

    # Defines a static method for classifying trades without using instance state.
    @staticmethod
    # Defines a method that estimates whether trades are buys or sells.
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

        # Copies the input DataFrame to avoid modifying the original.
        result = trades.copy()

        # Checks whether the exchange provides buyer-maker information.
        if "is_buyer_maker" in result.columns:

            # Retrieves the buyer-maker values from the DataFrame.
            maker = result["is_buyer_maker"]

            # Initially labels every trade as having an unknown direction.
            result["trade_side"] = "unknown"

            # Identifies rows where buyer-maker information is available.
            valid = maker.notna()

            # Maps True to sell and False to buy for valid rows.
            result.loc[valid, "trade_side"] = (
                maker.loc[valid]
                .map({True: "sell", False: "buy"})
            )

            # Returns the classified trades without applying the fallback rule.
            return result

        # Checks whether price data is available for the fallback method.
        if "price" not in result.columns:
            # Raises an error because price changes are needed for classification.
            raise ValueError(
                "Trade classification requires price data."
            )

        # Converts the price column into numeric values.
        price = pd.to_numeric(result["price"], errors="raise")

        # Calculates the difference between each price and the previous price.
        change = price.diff()

        # Initially marks every trade as having an unknown direction.
        result["trade_side"] = "unknown"

        # Classifies a trade as a buy when its price exceeds the previous price.
        result.loc[change > 0, "trade_side"] = "buy"

        # Classifies a trade as a sell when its price is below the previous price.
        result.loc[change < 0, "trade_side"] = "sell"

        # Returns the DataFrame with its estimated trade directions.
        return result

    # Defines an instance method that calculates overall trade statistics.
    def analyze_trades(
        # Provides access to the current MarketAnalytics instance.
        self,
        # Accepts the trade records as a Pandas DataFrame.
        trades: pd.DataFrame,
    ) -> dict:
        """Return aggregate trade statistics."""

        # Validates the input and calculates the value of each trade.
        result = self._validate_trades(trades)

        # Adds a trade_side column using exchange data or the tick-rule fallback.
        result = self.classify_trades(result)

        # Creates a Boolean mask identifying trades at or above the large-trade threshold.
        large = (
            result["trade_value"]
            >= self.config.large_trade_threshold
        )

        # Creates a Boolean mask identifying trades classified as buys.
        buy = result["trade_side"].eq("buy")

        # Creates a Boolean mask identifying trades classified as sells.
        sell = result["trade_side"].eq("sell")

        # Creates a dictionary containing the calculated market statistics.
        stats = {
            # Records the trading symbol from the configuration.
            "symbol": self.config.symbol,

            # Counts the number of rows in the DataFrame.
            "trade_count": int(len(result)),

            # Adds together the quantities of all trades.
            "total_volume": float(result["quantity"].sum()),

            # Adds together the monetary values of all trades.
            "total_traded_value": float(
                result["trade_value"].sum()
            ),

            # Calculates average trade quantity, returning zero for empty input.
            "average_trade_size": float(
                result["quantity"].mean()
            ) if len(result) else 0.0,

            # Calculates average monetary trade value, returning zero if empty.
            "average_trade_value": float(
                result["trade_value"].mean()
            ) if len(result) else 0.0,

            # Counts trades classified as buys.
            "buy_trade_count": int(buy.sum()),

            # Counts trades classified as sells.
            "sell_trade_count": int(sell.sum()),

            # Counts trades whose direction could not be determined.
            "unknown_trade_count": int(
                result["trade_side"].eq("unknown").sum()
            ),

            # Adds the quantities of buy-classified trades.
            "buy_volume": float(
                result.loc[buy, "quantity"].sum()
            ),

            # Adds the quantities of sell-classified trades.
            "sell_volume": float(
                result.loc[sell, "quantity"].sum()
            ),

            # Counts trades whose monetary value meets the large-trade threshold.
            "large_trade_count": int(large.sum()),

            # Adds the quantities of trades meeting the large-trade threshold.
            "large_trade_volume": float(
                result.loc[large, "quantity"].sum()
            ),

            # Adds the monetary values of trades meeting the threshold.
            "large_trade_value": float(
                result.loc[large, "trade_value"].sum()
            ),
        }

        # Returns the completed statistics dictionary.
        return stats

    # Defines an instance method for calculating statistics over rolling time windows.
    def rolling_statistics(
        # Provides access to the current MarketAnalytics instance.
        self,
        # Accepts trade records as a Pandas DataFrame.
        trades: pd.DataFrame,
    ) -> pd.DataFrame:
        """Calculate rolling trade statistics by timestamp."""

        # Validates the trade records and calculates their monetary values.
        result = self._validate_trades(trades)

        # Checks whether timestamps are available for time-based calculations.
        if "timestamp" not in result.columns:
            # Raises an error if time-based calculations cannot be performed.
            raise ValueError(
                "Rolling statistics require a timestamp column."
            )

        # Adds a trade_side column to classify trades as buys, sells, or unknown.
        result = self.classify_trades(result)

        # Sorts trades chronologically by timestamp.
        result = result.sort_values("timestamp")

        # Sets timestamp as the DataFrame index for time-based rolling calculations.
        result = result.set_index("timestamp")

        # Assigns a count of one to each trade so counts can be summed.
        result["trade_count"] = 1

        # Keeps the trade quantity for buys and assigns zero to other trades.
        result["buy_volume"] = result["quantity"].where(
            result["trade_side"].eq("buy"), 0.0
        )

        # Keeps the trade quantity for sells and assigns zero to other trades.
        result["sell_volume"] = result["quantity"].where(
            result["trade_side"].eq("sell"), 0.0
        )

        # Marks large trades with one and other trades with zero.
        result["large_trade_count"] = (
            result["trade_value"]
            >= self.config.large_trade_threshold
        ).astype(int)

        # Retrieves the configured rolling-window duration, such as five minutes.
        window = self.config.rolling_window

        # Selects the columns that will be aggregated over the rolling window.
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

        # Creates an output DataFrame using the trade timestamps as its index.
        output = pd.DataFrame(index=result.index)

        # Calculates total trade quantity within each rolling window.
        output["volume"] = rolling["quantity"].sum()

        # Calculates total monetary trade value within each rolling window.
        output["traded_value"] = rolling["trade_value"].sum()

        # Calculates the number of trades within each rolling window.
        output["trade_count"] = rolling["trade_count"].sum()

        # Calculates average trade quantity within each rolling window.
        output["average_trade_size"] = rolling["quantity"].mean()

        # Calculates total buy volume within each rolling window.
        output["buy_volume"] = rolling["buy_volume"].sum()

        # Calculates total sell volume within each rolling window.
        output["sell_volume"] = rolling["sell_volume"].sum()

        # Counts large trades within each rolling window.
        output["large_trade_count"] = (
            rolling["large_trade_count"].sum()
        )

        # Returns the rolling statistics indexed by timestamp.
        return output

    # Defines a static method to calculate the bid-ask spread.
    @staticmethod
    # Accepts the best available bid and ask prices.
    def calculate_spread(
        # Represents the highest price a buyer is currently offering.
        bid: float,
        # Represents the lowest price a seller is currently requesting.
        ask: float,
    ) -> dict:
        """Calculate absolute and relative bid-ask spread."""

        # Checks whether either quoted price is negative.
        if bid < 0 or ask < 0:
            # Raises an error if either price is invalid.
            raise ValueError("Bid and ask cannot be negative.")

        # Checks whether the ask price is lower than the bid price.
        if ask < bid:
            # Raises an error because the supplied quotes are crossed.
            raise ValueError("Ask cannot be lower than bid.")

        # Calculates the absolute spread between the ask and bid.
        spread = ask - bid

        # Calculates the midpoint between the bid and ask prices.
        midpoint = (ask + bid) / 2

        # Creates a dictionary containing the spread calculations.
        return {
            # Returns the bid as a floating-point number.
            "bid": float(bid),

            # Returns the ask as a floating-point number.
            "ask": float(ask),

            # Returns the absolute difference between ask and bid.
            "spread": float(spread),

            # Converts the spread to basis points relative to the midpoint.
            # One basis point equals 0.01 percent.
            # Returns zero when the midpoint is zero to avoid division by zero.
            "spread_bps": (
                float(spread / midpoint * 10_000)
                if midpoint > 0 else 0.0
            ),

            # Returns the midpoint as a floating-point number.
            "midpoint": float(midpoint),
        }
