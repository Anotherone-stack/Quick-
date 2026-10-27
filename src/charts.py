
# Allow type annotations to refer to types that may be defined later.
from __future__ import annotations

# Import deque, a list-like structure that can automatically discard old entries.
from collections import deque

# Import Optional to indicate that a value can be a specific type or None.
from typing import Optional

# Import pandas to store, sort, and calculate statistics on trade data.
import pandas as pd

# Import Plotly graph objects to create interactive charts.
import plotly.graph_objects as go

# Import make_subplots to create charts that can support multiple axes.
from plotly.subplots import make_subplots


# Define a class that manages trade data and builds interactive price charts.
class LivePriceChart:

    # Describe the purpose of the class.
    """Build interactive price charts from recent trade data."""

    # Initialize a new LivePriceChart object with configurable settings.
    def __init__(
        self,
        symbol: str = "BTCUSDT",  # Set the default market symbol to Bitcoin/USDT.
        window: int = 100,  # Store the configured window size.
        rolling_window: int = 20,  # Calculate rolling statistics over 20 trades by default.
        max_points: int = 2000,  # Keep no more than 2,000 trade records in memory.
    ) -> None:  # Indicate that this method does not return a value.

        # Reject a window size smaller than one.
        if window < 1:
            raise ValueError("window must be positive")

        # Reject a rolling window smaller than one.
        if rolling_window < 1:
            raise ValueError("rolling_window must be positive")

        # Reject a maximum point limit smaller than one.
        if max_points < 1:
            raise ValueError("max_points must be positive")

        # Save the market symbol on this object.
        self.symbol = symbol

        # Save the configured window size.
        self.window = window

        # Save the rolling statistics window size.
        self.rolling_window = rolling_window

        # Save the maximum number of trades to retain.
        self.max_points = max_points

        # Create a bounded queue that automatically removes the oldest trade
        # whenever a new trade exceeds the maximum capacity.
        self._trades: deque[dict] = deque(maxlen=max_points)

    # Define a method that adds one trade to the chart's stored data.
    def add_trade(
        self,
        timestamp,  # Receive the time at which the trade occurred.
        price: float,  # Receive the trade price as a floating-point number.
        quantity: Optional[float] = None,  # Optionally receive the traded quantity.
    ) -> None:  # Indicate that this method does not return a value.

        # Describe what this method does.
        """Append a trade received from the market-data stream."""

        # Convert the supplied price to a floating-point number.
        price = float(price)

        # Check that the trade price is greater than zero.
        if price <= 0:
            raise ValueError("Price must be positive")

        # Create a dictionary containing the trade timestamp and price.
        record = {
            # Convert the timestamp to a timezone-aware UTC datetime.
            "timestamp": pd.to_datetime(timestamp, utc=True),

            # Store the validated numeric trade price.
            "price": price,
        }

        # Include quantity only if the caller supplied it.
        if quantity is not None:

            # Convert the quantity to a floating-point number.
            record["quantity"] = float(quantity)

        # Append the trade to the bounded deque.
        self._trades.append(record)

    # Define a method that adds multiple trades from a pandas DataFrame.
    def add_trades(self, trades: pd.DataFrame) -> None:

        # Describe the purpose of this method.
        """Append a batch of trades with timestamp and price columns."""

        # Define the column names that every trade must contain.
        required = {"timestamp", "price"}

        # Find which required columns are absent from the DataFrame.
        missing = required - set(trades.columns)

        # Raise an error if any required columns are missing.
        if missing:
            raise ValueError(
                f"Missing required columns: {sorted(missing)}"
            )

        # Convert each DataFrame row into a dictionary and iterate over it.
        for row in trades.to_dict("records"):

            # Add the current row using the single-trade method.
            self.add_trade(
                timestamp=row["timestamp"],  # Pass the trade timestamp.
                price=row["price"],  # Pass the trade price.
                quantity=row.get("quantity"),  # Pass quantity if the column exists.
            )

    # Define a method that returns the stored data and rolling statistics.
    def get_data(self) -> pd.DataFrame:

        # Describe the data returned by this method.
        """Return prices and rolling statistics for recent trades."""

        # Define the columns expected in the returned DataFrame.
        columns = [
            "timestamp",  # The time of each trade.
            "price",  # The recorded trade price.
            "rolling_high",  # The highest price in the rolling window.
            "rolling_low",  # The lowest price in the rolling window.
            "rolling_average",  # The average price in the rolling window.
        ]

        # Check whether any trades have been stored.
        if not self._trades:

            # Return an empty DataFrame with the expected column names.
            return pd.DataFrame(columns=columns)

        # Convert the stored trade dictionaries into a pandas DataFrame.
        data = pd.DataFrame(list(self._trades))

        # Sort trades chronologically and reset the row index.
        data = data.sort_values("timestamp").reset_index(drop=True)

        # Create a rolling calculation over the most recent N trade prices.
        # min_periods=1 allows calculations before the window is full.
        rolling = data["price"].rolling(
            window=self.rolling_window,  # Set the number of trades per window.
            min_periods=1,  # Calculate results with at least one available trade.
        )

        # Calculate the highest price in each rolling window.
        data["rolling_high"] = rolling.max()

        # Calculate the lowest price in each rolling window.
        data["rolling_low"] = rolling.min()

        # Calculate the average price in each rolling window.
        data["rolling_average"] = rolling.mean()

        # Return the trade data with its calculated statistics.
        return data

    # Define a method that constructs an interactive Plotly figure.
    def build_figure(self) -> go.Figure:

        # Describe what the method creates.
        """Create a Plotly figure for browser or notebook display."""

        # Retrieve the stored trade data and rolling statistics.
        data = self.get_data()

        # Create a subplot with support for a secondary vertical axis.
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # Add the actual trade price series to the figure.
        fig.add_trace(
            go.Scatter(
                x=data["timestamp"],  # Use trade timestamps on the horizontal axis.
                y=data["price"],  # Use trade prices on the vertical axis.
                name="Trade price",  # Name the series in the chart legend.
                mode="lines",  # Display the prices as a line.
                line=dict(color="#2196F3", width=1.5),  # Set the line color and width.
            ),
            secondary_y=False,  # Plot the prices on the primary vertical axis.
        )

        # Add a series showing the rolling maximum price.
        fig.add_trace(
            go.Scatter(
                x=data["timestamp"],  # Use trade timestamps on the horizontal axis.
                y=data["rolling_high"],  # Plot the rolling high values.
                name=f"Rolling high ({self.rolling_window})",  # Label the series with its window size.
                mode="lines",  # Draw a line.
                line=dict(color="#4CAF50", width=1, dash="dot"),  # Use a dotted green line.
            ),
            secondary_y=False,  # Use the primary vertical axis.
        )

        # Add a series showing the rolling minimum price.
        fig.add_trace(
            go.Scatter(
                x=data["timestamp"],  # Use trade timestamps on the horizontal axis.
                y=data["rolling_low"],  # Plot the rolling low values.
                name=f"Rolling low ({self.rolling_window})",  # Label the series with its window size.
                mode="lines",  # Draw a line.
                line=dict(color="#F44336", width=1, dash="dot"),  # Use a dotted red line.
            ),
            secondary_y=False,  # Use the primary vertical axis.
        )

        # Add a series showing the rolling average price.
        fig.add_trace(
            go.Scatter(
                x=data["timestamp"],  # Use trade timestamps on the horizontal axis.
                y=data["rolling_average"],  # Plot the rolling average values.
                name=f"Rolling average ({self.rolling_window})",  # Label the series.
                mode="lines",  # Draw a line.
                line=dict(color="#FF9800", width=2),  # Use a thicker orange line.
            ),
            secondary_y=False,  # Use the primary vertical axis.
        )

        # Configure the overall appearance of the chart.
        fig.update_layout(
            title=f"{self.symbol} Live Price",  # Set the chart title using the market symbol.
            template="plotly_dark",  # Apply Plotly's dark theme.
            hovermode="x unified",  # Display hover values together for each time position.
            legend=dict(orientation="h", y=1.12),  # Place the legend horizontally above the chart.
            margin=dict(l=50, r=30, t=90, b=45),  # Set chart margins.
        )

        # Label the horizontal axis and enable its range slider.
        fig.update_xaxes(
            title_text="Time",
            rangeslider_visible=True,
        )

        # Label the primary vertical axis.
        fig.update_yaxes(
            title_text="Price",
            secondary_y=False,
        )

        # Return the completed interactive chart.
        return fig

    # Define a method that exports the chart as HTML.
    def to_html(self, full_html: bool = False) -> str:

        # Describe the purpose of this method.
        """Export the chart for embedding in a browser dashboard."""

        # Build the figure and convert it into HTML.
        return self.build_figure().to_html(
            full_html=full_html,  # Return a full HTML document only when requested.
            include_plotlyjs="cdn",  # Load Plotly JavaScript from a CDN.
        )


# ---------- CONNECT TO ALPACA ----------

# Define a callback that receives an individual trade from Alpaca.
def handle_trade(trade):

    # Add the incoming trade to the LivePriceChart instance.
    chart.add_trade(
        timestamp=trade.timestamp,  # Pass the trade's timestamp.
        price=trade.price,  # Pass the trade's execution price.
        quantity=trade.size,  # Pass the number of units traded.
    )


# Create a chart object for the BTC/USDT market.
# This object stores the trades and builds the chart.
chart = LivePriceChart(
    symbol="BTCUSDT",
    rolling_window=20,
    max_points=2000,
)
