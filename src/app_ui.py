
# Import datetime to display the current date.
from datetime import datetime

# Import Streamlit to build the web dashboard.
import streamlit as st

# Import pandas to manage stock market data.
import pandas as pd

# Import Plotly to create interactive charts.
import plotly.graph_objects as go

# Import yfinance to retrieve stock prices.
import yfinance as yf

from src.live_monitor import LiveMonitor


# Configure the Streamlit page.
st.set_page_config(
    page_title="Stocky | Market Dashboard",  # Browser tab title.
    page_icon="📈",  # Browser tab icon.
    layout="wide",  # Use the full browser width.
    initial_sidebar_state="expanded",  # Show the sidebar initially.
)


# ---------- THEME ----------

# Apply custom CSS styling to the dashboard.
st.markdown("""
<style>
/* Import the DM Sans font. */
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');

/* Set the application font. */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* Style the main application background. */
.stApp {
    background: #0c0f14;
    color: #f3f5f7;
}

/* Style the sidebar. */
section[data-testid="stSidebar"] {
    background: #11151c;
    border-right: 1px solid #242a34;
}

/* Set sidebar text colors. */
section[data-testid="stSidebar"] * {
    color: #dce2ea;
}

/* Adjust the main content spacing. */
.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1500px;
}

/* Style the headings. */
h1, h2, h3 {
    color: #f4f6fa !important;
    letter-spacing: -0.6px;
}

/* Style paragraph and label text. */
p, label {
    color: #9ca8b8;
}

/* Style metric cards. */
div[data-testid="stMetric"] {
    background: #151a22;
    border: 1px solid #272e39;
    border-radius: 14px;
    padding: 18px 20px;
}

/* Style metric labels. */
div[data-testid="stMetricLabel"] {
    color: #99a5b5;
}

/* Style metric values. */
div[data-testid="stMetricValue"] {
    color: #f5f7fa;
    font-size: 1.65rem;
}

/* Style metric changes. */
div[data-testid="stMetricDelta"] {
    font-size: 0.85rem;
}

/* Style Plotly chart containers. */
div[data-testid="stPlotlyChart"] {
    background: #151a22;
    border: 1px solid #272e39;
    border-radius: 14px;
    padding: 8px;
}

/* Style the data table. */
div[data-testid="stDataFrame"] {
    border: 1px solid #272e39;
    border-radius: 12px;
}

/* Style horizontal divider lines. */
hr {
    border-color: #272e39;
}

/* Style captions. */
.stCaption {
    color: #7e8b9d;
}
</style>
""", unsafe_allow_html=True)  # Allow custom CSS to render.


# Define the color for positive stock movements.
GREEN = "#35d49a"

# Define the color for negative stock movements.
RED = "#ff647c"

# Define the muted text color.
MUTED = "#7f8b9d"

# Define the chart panel background color.
PANEL = "#151a22"


# ---------- DATA HELPERS ----------

# Cache historical data for five minutes.
@st.cache_data(ttl=300, show_spinner=False)
def get_history(ticker, period):

    # Download historical stock prices.
    data = yf.Ticker(ticker).history(
        period=period,
        auto_adjust=True
    )

    # Return an empty DataFrame if no data is available.
    if data.empty:
        return pd.DataFrame()

    # Remove records without closing prices.
    data = data.dropna(subset=["Close"])

    # Ensure the index contains datetime values.
    data.index = pd.to_datetime(data.index)

    # Return the cleaned historical data.
    return data


# Cache stock quote calculations for five minutes.
@st.cache_data(ttl=300, show_spinner=False)
def get_quote(ticker):

    # Retrieve five days of stock history.
    data = get_history(ticker, "5d")

    # Return None if no data is available.
    if len(data) < 1:
        return None

    # Get the latest closing price.
    price = float(data["Close"].iloc[-1])

    # Get the previous closing price if available.
    previous = float(data["Close"].iloc[-2]) if len(data) > 1 else price

    # Calculate the price change.
    change = price - previous

    # Calculate the percentage change.
    pct = (change / previous * 100) if previous else 0

    # Return the price and both change values.
    return price, change, pct


# Format a number as a dollar amount.
def money(value):

    # Return a formatted dollar value.
    return f"${value:,.2f}"


# ---------- CHART CREATION ----------

# Create a chart using stock data and the selected chart type.
def make_chart(data, ticker, chart_type="Area"):

    # Create a new Plotly figure.
    fig = go.Figure()

    # Choose green for an overall rise or red for an overall fall.
    color = GREEN if data["Close"].iloc[-1] >= data["Close"].iloc[0] else RED

    # Check whether the user selected a candlestick chart.
    if chart_type == "Candlestick":

        # Add the candlestick chart.
        fig.add_trace(go.Candlestick(
            x=data.index,  # Horizontal axis uses dates.
            open=data["Open"],  # Opening prices.
            high=data["High"],  # Highest prices.
            low=data["Low"],  # Lowest prices.
            close=data["Close"],  # Closing prices.
            increasing_line_color=GREEN,  # Green rising candles.
            decreasing_line_color=RED,  # Red falling candles.
            name=ticker,  # Name the chart after the ticker.
        ))

    # Otherwise, create a line or area chart.
    else:

        # Add the closing price line.
        fig.add_trace(go.Scatter(
            x=data.index,  # Dates along the horizontal axis.
            y=data["Close"],  # Closing prices along the vertical axis.
            mode="lines",  # Draw a line.
            name=ticker,  # Name the chart trace.
            line=dict(color=color, width=2.5),  # Set line appearance.
            fill="tozeroy" if chart_type == "Area" else None,  # Fill area charts.
            fillcolor="rgba(53,212,154,0.09)" if color == GREEN else "rgba(255,100,124,0.09)",  # Set the fill color.
            hovertemplate="$%{y:,.2f}<extra></extra>",  # Show prices on hover.
        ))

    # Configure the chart layout.
    fig.update_layout(
        height=390,  # Set chart height.
        margin=dict(l=10, r=15, t=15, b=10),  # Set chart margins.
        paper_bgcolor=PANEL,  # Set the outer background.
        plot_bgcolor=PANEL,  # Set the plot background.
        font=dict(color="#9ca8b8", family="DM Sans"),  # Set chart typography.
        showlegend=False,  # Hide the legend.
        hovermode="x unified",  # Combine hover information.
        xaxis=dict(
            showgrid=False,  # Hide vertical grid lines.
            zeroline=False,  # Hide the zero line.
            showspikes=True,  # Show hover guide lines.
            spikemode="across",  # Extend guides across the chart.
            spikecolor="#657186",  # Set guide line color.
            spikethickness=1,  # Set guide line thickness.
        ),
        yaxis=dict(
            side="right",  # Put price labels on the right.
            tickprefix="$",  # Prefix prices with a dollar sign.
            showgrid=True,  # Show horizontal grid lines.
            gridcolor="#252c36",  # Set grid color.
            zeroline=False,  # Hide the zero line.
        ),
    )

    # Return the completed figure.
    return fig

# ---------- SIDEBAR ----------

# Place navigation and watchlist elements in the sidebar.
with st.sidebar:

    # Display the application name.
    st.markdown("# 📈 Stocky")

    # Display the dashboard subtitle.
    st.caption("MARKET INTELLIGENCE")

    # Add a divider.
    st.divider()

    # Create the workspace navigation menu.
    page = st.radio(
        "WORKSPACE",  # Navigation label.
        ["Overview", "Watchlist", "Explore"],  # Available pages.
        label_visibility="visible",  # Show the label.
    )

    # Add a divider below navigation.
    st.divider()

    # Display the watchlist heading.
    st.markdown("**YOUR WATCHLIST**")

    # Define the default watchlist.
    watchlist = ["AAPL", "NVDA", "MSFT", "GOOGL", "AMZN"]

    # Display each ticker in the sidebar.
    for symbol in watchlist:
        st.markdown(f"↗  **{symbol}**")

    # Add a divider above the footer.
    st.divider()

    # Credit the market data provider.
    st.caption("Market data by Yahoo Finance")

    # Warn users that prices may be delayed.
    st.caption("Prices may be delayed.")


# ---------- HEADER ----------

# Create columns for the title and date.
col_title, col_time = st.columns([3, 1])

# Display the page title and subtitle.
with col_title:
    st.title("Market overview" if page == "Overview" else page)
    st.caption("Track the market. Discover opportunities. Stay informed.")

# Display the current date on the right.
with col_time:
    st.markdown(
        f"<div style='text-align:right;color:{MUTED};padding-top:22px'>"
        f"{datetime.now().strftime('%b %d, %Y')}</div>",
        unsafe_allow_html=True,
    )

# Add vertical spacing.
st.write("")


# ---------- MARKET SUMMARY ----------

# Display the market snapshot heading.
st.markdown("### Market snapshot")

# Define market indices and their Yahoo Finance symbols.
indices = [
    ("S&P 500", "^GSPC"),
    ("NASDAQ", "^IXIC"),
    ("DOW JONES", "^DJI"),
    ("RUSSELL 2000", "^RUT"),
]

# Create four columns for the indices.
cols = st.columns(4)

# Loop through the columns and indices together.
for col, (label, ticker) in zip(cols, indices):

    # Display one index inside its column.
    with col:

        # Group the index information in a container.
        with st.container():

            # Display the index name.
            st.caption(label)

            # Attempt to retrieve its latest quote.
            try:
                quote = get_quote(ticker)

                # Display the quote when available.
                if quote:
                    price, change, pct = quote

                    # Display the index value and its change.
                    st.metric(
                        label="",
                        value=f"{price:,.2f}",
                        delta=f"{change:+,.2f} ({pct:+.2f}%)",
                    )

                # Show a fallback when no quote is returned.
                else:
                    st.metric(label="", value="Unavailable", delta=None)

            # Handle errors for individual indices.
            except Exception:
                st.metric(label="", value="Unavailable", delta=None)

# Add vertical spacing.
st.write("")

# ---------- MAIN CHART AND STOCK DETAILS ----------

# Create a wide chart column and a narrower side column.
left, right = st.columns([2.15, 1], gap="large")

# Build the main chart in the left column.
with left:

    # Display the stock performance heading.
    st.markdown("### Stock performance")

    # Create columns for the stock, period, and chart selectors.
    controls = st.columns([1.4, 1, 1])

    # Create the stock selector.
    with controls[0]:
        ticker = st.selectbox(
            "Stock",
            ["NVDA", "AAPL", "MSFT", "GOOGL", "AMZN",
             "META", "TSLA", "AMD", "NFLX", "BRK-B"],
            index=0,
        )

    # Create the period selector.
    with controls[1]:
        period_label = st.selectbox(
            "Period",
            ["1D", "5D", "1M", "3M", "6M", "1Y", "5Y"],
            index=3,
        )

    # Create the chart style selector.
    with controls[2]:
        chart_type = st.selectbox(
            "Chart",
            ["Area", "Line", "Candlestick"],
        )

    # Map display labels to Yahoo Finance history periods and intervals.
    period_map = {
        "1D": ("1d", "5m"),
        "5D": ("5d", "15m"),
        "1M": ("1mo", "1d"),
        "3M": ("3mo", "1d"),
        "6M": ("6mo", "1d"),
        "1Y": ("1y", "1d"),
        "5Y": ("5y", "1wk"),
    }

    # Get the selected period and interval.
    period, interval = period_map[period_label]

    # Attempt to load the selected stock's history.
    try:
        history = get_history(ticker, period)

        # Continue if historical data is available.
        if not history.empty:

            # Get the latest closing price.
            latest = float(history["Close"].iloc[-1])

            # Get the first closing price in the selected period.
            first = float(history["Close"].iloc[0])

            # Calculate the price difference.
            change = latest - first

            # Calculate the percentage difference.
            pct = change / first * 100 if first else 0

            # Display the current price and change.
            st.markdown(
                f"<div style='padding:4px 0 12px'>"
                f"<span style='font-size:30px;font-weight:700;color:#f5f7fa'>"
                f"{money(latest)}</span>"
                f"<span style='margin-left:12px;color:{GREEN if change >= 0 else RED}'>"
                f"{change:+.2f} ({pct:+.2f}%)</span></div>",
                unsafe_allow_html=True,
            )

            # Generate and display the selected chart.
            st.plotly_chart(
                make_chart(history, ticker, chart_type),
                use_container_width=True,
                config={"displayModeBar": False},
            )

            # Get the latest trading volume if available.
            volume = float(history["Volume"].iloc[-1]) if "Volume" in history else 0

            # Create three columns for summary statistics.
            m1, m2, m3 = st.columns(3)

            # Display the highest price in the selected period.
            m1.metric("Period high", money(history["High"].max()))

            # Display the lowest price in the selected period.
            m2.metric("Period low", money(history["Low"].min()))

            # Display the latest trading volume.
            m3.metric("Latest volume", f"{volume:,.0f}")

        # Handle empty historical data.
        else:
            st.warning("No price history returned. Try another symbol or period.")

    # Handle download or chart errors.
    except Exception as exc:
        st.error("Unable to load stock data. Check your internet connection or try again.")
        st.caption(str(exc))


# ---------- WATCHLIST PANEL ----------

# Build the watchlist in the right column.
with right:

    # Display the watchlist heading.
    st.markdown("### Your watchlist")

    # Display a short description.
    st.caption("Latest available prices")

    # Loop through each watchlist ticker.
    for symbol in watchlist:

        # Attempt to retrieve the stock quote.
        try:
            quote = get_quote(symbol)

            # Display a card when quote data exists.
            if quote:
                price, change, pct = quote

                # Choose green for gains and red for losses.
                color = GREEN if pct >= 0 else RED

                # Render a stock information card.
                st.markdown(
                    f"""
                    <div style="display:flex;justify-content:space-between;
                    align-items:center;padding:15px 12px;margin-bottom:8px;
                    background:#151a22;border:1px solid #272e39;border-radius:12px">

                      <!-- Display the ticker and asset category. -->
                      <div>
                        <div style="font-weight:700;color:#f3f5f7">{symbol}</div>
                        <div style="font-size:12px;color:#7f8b9d">US equity</div>
                      </div>

                      <!-- Display the latest price and percentage change. -->
                      <div style="text-align:right">
                        <div style="font-weight:600;color:#f3f5f7">${price:,.2f}</div>
                        <div style="font-size:12px;color:{color}">{pct:+.2f}%</div>
                      </div>

                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # Handle errors for an individual ticker.
        except Exception:
            st.caption(f"{symbol} · Quote unavailable")

    # Add spacing before quick lookup.
    st.write("")

    # Display the quick lookup heading.
    st.markdown("### Quick lookup")

    # Create an input for a custom stock ticker.
    custom_ticker = st.text_input("Ticker symbol", placeholder="e.g. COST")

    # Process the ticker when the button is clicked.
    if st.button("Analyze stock", use_container_width=True):

        # Remove spaces and convert the ticker to uppercase.
        cleaned = custom_ticker.strip().upper()

        # Continue if the input is not empty.
        if cleaned:

            # Save the ticker in session state.
            st.session_state["selected_ticker"] = cleaned

            # Inform the user how to view the stock.
            st.info(
                f"Ticker entered: {cleaned}. "
                "Select it from the chart selector to view its history."
            )

# ---------- MARKET MOVERS TABLE ----------

# Add vertical spacing.
st.write("")

# Add a horizontal divider.
st.divider()

# Display the market movers heading.
st.markdown("### Market movers")

# Describe the table's contents.
st.caption("Latest available data for popular stocks")

# Define the stocks to include in the table.
symbols = [
    "NVDA", "AAPL", "MSFT", "GOOGL", "AMZN",
    "META", "TSLA", "AMD", "NFLX", "JPM"
]

# Create an empty list for the collected stock records.
rows = []

# Show a loading spinner while fetching quotes.
with st.spinner("Loading market data..."):

    # Loop through every stock symbol.
    for symbol in symbols:

        # Attempt to retrieve the quote.
        try:
            quote = get_quote(symbol)

            # Store the quote when available.
            if quote:

                # Unpack the returned quote values.
                price, change, pct = quote

                # Add the stock information to the rows list.
                rows.append({
                    "Ticker": symbol,  # Stock symbol.
                    "Last price": price,  # Latest closing price.
                    "Change": change,  # Absolute price change.
                    "Change (%)": pct,  # Percentage price change.
                })

        # Skip a stock if its request fails.
        except Exception:
            pass

# Display the table if at least one quote was retrieved.
if rows:

    # Convert the records into a DataFrame and sort by percentage change.
    table = pd.DataFrame(rows).sort_values(
        "Change (%)",
        ascending=False
    )

    # Display the market movers table.
    st.dataframe(
        table,  # Data to display.
        use_container_width=True,  # Use the available page width.
        hide_index=True,  # Hide row numbers.
        column_config={

            # Configure the ticker column.
            "Ticker": st.column_config.TextColumn("Ticker"),

            # Format the last price as dollars.
            "Last price": st.column_config.NumberColumn(
                "Last price",
                format="$%.2f"
            ),

            # Format absolute changes as signed dollar amounts.
            "Change": st.column_config.NumberColumn(
                "Change",
                format="$%+.2f"
            ),

            # Format percentage changes with a percent symbol.
            "Change (%)": st.column_config.NumberColumn(
                "Change (%)",
                format="%+.2f%%"
            ),
        },
    )

# Display a message if no market data was retrieved.
else:
    st.info("Market data is temporarily unavailable. Please try again later.")


# ---------- LIVE SPCX MONITOR ----------

@st.fragment(run_every="2s")
def render_live_monitor():
    st.markdown("### SPCX live market monitor")
    st.caption(
        "Live IEX quotes and trades from Alpaca. Trade direction is an estimate."
    )

    if "live_monitor" not in st.session_state:
        st.session_state["live_monitor"] = LiveMonitor()
    monitor = st.session_state["live_monitor"]
    market_data = st.session_state.get("live_market_data")
    is_running = market_data is not None and market_data.is_running

    start_col, stop_col, status_col = st.columns([1, 1, 3])
    start_feed = start_col.button(
        "Start feed", disabled=is_running, key="live_monitor_start"
    )
    stop_feed = stop_col.button(
        "Stop feed", disabled=not is_running, key="live_monitor_stop"
    )

    if start_feed:
        try:
            from alpaca.data.enums import DataFeed

            from src.market_data import AlpacaMarketData

            market_data = AlpacaMarketData(
                [monitor.symbol],
                on_trade=monitor.record_trade,
                on_quote=monitor.record_quote,
                feed=DataFeed.IEX,
            )
            market_data.start()
            st.session_state["live_market_data"] = market_data
        except Exception as exc:
            st.error(f"Unable to start the Alpaca feed: {exc}")

    if stop_feed and market_data is not None:
        market_data.stop()

    market_data = st.session_state.get("live_market_data")
    connection = market_data.status() if market_data is not None else {
        "running": False,
        "connected": False,
        "last_error": None,
        "reconnect_attempts": 0,
    }
    if connection["connected"]:
        status_col.success("LIVE")
    elif connection["running"]:
        status_col.info("CONNECTING / RECONNECTING")
    else:
        status_col.caption("DISCONNECTED")

    if connection["last_error"]:
        st.warning(
            f"Stream error: {connection['last_error']} "
            f"(reconnect attempts: {connection['reconnect_attempts']})"
        )

    snapshot = monitor.snapshot()
    quote = snapshot["quote"] or {}
    bid_col, ask_col = st.columns(2)
    bid_col.metric(
        "Bid",
        f"${quote['bid']:,.2f}" if quote else "—",
        f"Size: {quote['bid_size']:,}" if quote else None,
    )
    ask_col.metric(
        "Ask",
        f"${quote['ask']:,.2f}" if quote else "—",
        f"Size: {quote['ask_size']:,}" if quote else None,
    )

    trades_col, large_col, last_col = st.columns(3)
    trades_col.metric("Trades", f"{snapshot['trade_count']:,}")
    large_col.metric("Large trades", f"{snapshot['large_trade_count']:,}")
    last_price = snapshot["last_trade_price"]
    last_col.metric(
        "Last trade",
        f"${last_price:,.2f}" if last_price is not None else "—",
    )

    tape = pd.DataFrame(snapshot["trades"])
    if tape.empty:
        st.info("No trades received yet.")
    else:
        st.dataframe(
            tape[["time", "symbol", "price", "size", "side", "alert"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "time": st.column_config.TextColumn("TIME (ET)"),
                "symbol": st.column_config.TextColumn("SYMBOL"),
                "price": st.column_config.NumberColumn(
                    "PRICE", format="$%.2f"
                ),
                "size": st.column_config.NumberColumn(
                    "SHARES", format="%d"
                ),
                "side": st.column_config.TextColumn("ESTIMATED SIDE"),
                "alert": st.column_config.TextColumn("ALERT"),
            },
        )


st.divider()
render_live_monitor()


# ---------- FOOTER ----------

# Display the app credit and financial disclaimer.
st.caption(
    "Stocky UI concept · Market data provided by Yahoo Finance via yfinance. "
    "For informational purposes only; not investment advice."
)
