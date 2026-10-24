
from __future__ import annotations

from collections import deque
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


class LivePriceChart:
    """Build interactive price charts from recent trade data."""

    def __init__(
        self,
        symbol: str = "BTCUSDT",
        window: int = 100,
        rolling_window: int = 20,
        max_points: int = 2000,
    ) -> None:
        if window < 1:
            raise ValueError("window must be positive")
        if rolling_window < 1:
            raise ValueError("rolling_window must be positive")
        if max_points < 1:
            raise ValueError("max_points must be positive")

        self.symbol = symbol
        self.window = window
        self.rolling_window = rolling_window
        self.max_points = max_points
        self._trades: deque[dict] = deque(maxlen=max_points)

    def add_trade(
        self,
        timestamp,
        price: float,
        quantity: Optional[float] = None,
    ) -> None:
        """Append a trade received from the market-data stream."""
        price = float(price)

        if price <= 0:
            raise ValueError("Price must be positive")

        record = {
            "timestamp": pd.to_datetime(timestamp, utc=True),
            "price": price,
        }

        if quantity is not None:
            record["quantity"] = float(quantity)

        self._trades.append(record)

    def add_trades(self, trades: pd.DataFrame) -> None:
        """Append a batch of trades with timestamp and price columns."""
        required = {"timestamp", "price"}
        missing = required - set(trades.columns)

        if missing:
            raise ValueError(
                f"Missing required columns: {sorted(missing)}"
            )

        for row in trades.to_dict("records"):
            self.add_trade(
                timestamp=row["timestamp"],
                price=row["price"],
                quantity=row.get("quantity"),
            )

    def get_data(self) -> pd.DataFrame:
        """Return prices and rolling statistics for recent trades."""
        columns = [
            "timestamp",
            "price",
            "rolling_high",
            "rolling_low",
            "rolling_average",
        ]

        if not self._trades:
            return pd.DataFrame(columns=columns)

        data = pd.DataFrame(list(self._trades))
        data = data.sort_values("timestamp").reset_index(drop=True)

        # Compute statistics over the last N trades.
        rolling = data["price"].rolling(
            window=self.rolling_window,
            min_periods=1,
        )

        data["rolling_high"] = rolling.max()
        data["rolling_low"] = rolling.min()
        data["rolling_average"] = rolling.mean()

        return data

    def build_figure(self) -> go.Figure:
        """Create a Plotly figure for browser or notebook display."""
        data = self.get_data()

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        fig.add_trace(
            go.Scatter(
                x=data["timestamp"],
                y=data["price"],
                name="Trade price",
                mode="lines",
                line=dict(color="#2196F3", width=1.5),
            ),
            secondary_y=False,
        )

        fig.add_trace(
            go.Scatter(
                x=data["timestamp"],
                y=data["rolling_high"],
                name=f"Rolling high ({self.rolling_window})",
                mode="lines",
                line=dict(color="#4CAF50", width=1, dash="dot"),
            ),
            secondary_y=False,
        )

        fig.add_trace(
            go.Scatter(
                x=data["timestamp"],
                y=data["rolling_low"],
                name=f"Rolling low ({self.rolling_window})",
                mode="lines",
                line=dict(color="#F44336", width=1, dash="dot"),
            ),
            secondary_y=False,
        )

        fig.add_trace(
            go.Scatter(
                x=data["timestamp"],
                y=data["rolling_average"],
                name=f"Rolling average ({self.rolling_window})",
                mode="lines",
                line=dict(color="#FF9800", width=2),
            ),
            secondary_y=False,
        )

        fig.update_layout(
            title=f"{self.symbol} Live Price",
            template="plotly_dark",
            hovermode="x unified",
            legend=dict(orientation="h", y=1.12),
            margin=dict(l=50, r=30, t=90, b=45),
        )

        fig.update_xaxes(title_text="Time", rangeslider_visible=True)
        fig.update_yaxes(title_text="Price", secondary_y=False)

        return fig

    def to_html(self, full_html: bool = False) -> str:
        """Export the chart for embedding in a browser dashboard."""
        return self.build_figure().to_html(
            full_html=full_html,
            include_plotlyjs="cdn",
        )
#Connecting it to Alpaca Your stream callback can feed the chart:
    def handle_trade(trade):
    chart.add_trade(
        timestamp=trade.timestamp,
        price=trade.price,
        quantity=trade.size,
    )