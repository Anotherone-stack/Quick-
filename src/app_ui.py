1. Create app.py

from datetime import datetime
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf

st.set_page_config(
    page_title="Stocky | Market Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Theme ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}
.stApp {
    background: #0c0f14;
    color: #f3f5f7;
}
section[data-testid="stSidebar"] {
    background: #11151c;
    border-right: 1px solid #242a34;
}
section[data-testid="stSidebar"] * { color: #dce2ea; }
.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1500px;
}
h1, h2, h3 { color: #f4f6fa !important; letter-spacing: -0.6px; }
p, label { color: #9ca8b8; }
div[data-testid="stMetric"] {
    background: #151a22;
    border: 1px solid #272e39;
    border-radius: 14px;
    padding: 18px 20px;
}
div[data-testid="stMetricLabel"] { color: #99a5b5; }
div[data-testid="stMetricValue"] {
    color: #f5f7fa;
    font-size: 1.65rem;
}
div[data-testid="stMetricDelta"] { font-size: 0.85rem; }
div[data-testid="stPlotlyChart"] {
    background: #151a22;
    border: 1px solid #272e39;
    border-radius: 14px;
    padding: 8px;
}
div[data-testid="stDataFrame"] {
    border: 1px solid #272e39;
    border-radius: 12px;
}
hr { border-color: #272e39; }
.stCaption { color: #7e8b9d; }
</style>
""", unsafe_allow_html=True)

GREEN = "#35d49a"
RED = "#ff647c"
MUTED = "#7f8b9d"
PANEL = "#151a22"

# ---------- Data helpers ----------
@st.cache_data(ttl=300, show_spinner=False)
def get_history(ticker, period):
    data = yf.Ticker(ticker).history(period=period, auto_adjust=True)
    if data.empty:
        return pd.DataFrame()
    data = data.dropna(subset=["Close"])
    data.index = pd.to_datetime(data.index)
    return data

@st.cache_data(ttl=300, show_spinner=False)
def get_quote(ticker):
    data = get_history(ticker, "5d")
    if len(data) < 1:
        return None
    price = float(data["Close"].iloc[-1])
    previous = float(data["Close"].iloc[-2]) if len(data) > 1 else price
    change = price - previous
    pct = (change / previous * 100) if previous else 0
    return price, change, pct

def money(value):
    return f"${value:,.2f}"

def make_chart(data, ticker, chart_type="Area"):
    fig = go.Figure()
    color = GREEN if data["Close"].iloc[-1] >= data["Close"].iloc[0] else RED

    if chart_type == "Candlestick":
        fig.add_trace(go.Candlestick(
            x=data.index,
            open=data["Open"],
            high=data["High"],
            low=data["Low"],
            close=data["Close"],
            increasing_line_color=GREEN,
            decreasing_line_color=RED,
            name=ticker,
        ))
    else:
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data["Close"],
            mode="lines",
            name=ticker,
            line=dict(color=color, width=2.5),
            fill="tozeroy" if chart_type == "Area" else None,
            fillcolor="rgba(53,212,154,0.09)" if color == GREEN else "rgba(255,100,124,0.09)",
            hovertemplate="$%{y:,.2f}<extra></extra>",
        ))

    fig.update_layout(
        height=390,
        margin=dict(l=10, r=15, t=15, b=10),
        paper_bgcolor=PANEL,
        plot_bgcolor=PANEL,
        font=dict(color="#9ca8b8", family="DM Sans"),
        showlegend=False,
        hovermode="x unified",
        xaxis=dict(
            showgrid=False, zeroline=False,
            showspikes=True, spikemode="across",
            spikecolor="#657186", spikethickness=1,
        ),
        yaxis=dict(
            side="right", tickprefix="$",
            showgrid=True, gridcolor="#252c36",
            zeroline=False,
        ),
    )
    return fig

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("# 📈 Stocky")
    st.caption("MARKET INTELLIGENCE")
    st.divider()

    page = st.radio(
        "WORKSPACE",
        ["Overview", "Watchlist", "Explore"],
        label_visibility="visible",
    )

    st.divider()
    st.markdown("**YOUR WATCHLIST**")
    watchlist = ["AAPL", "NVDA", "MSFT", "GOOGL", "AMZN"]
    for symbol in watchlist:
        st.markdown(f"↗  **{symbol}**")

    st.divider()
    st.caption("Market data by Yahoo Finance")
    st.caption("Prices may be delayed.")

# ---------- Header ----------
col_title, col_time = st.columns([3, 1])
with col_title:
    st.title("Market overview" if page == "Overview" else page)
    st.caption("Track the market. Discover opportunities. Stay informed.")
with col_time:
    st.markdown(
        f"<div style='text-align:right;color:{MUTED};padding-top:22px'>"
        f"{datetime.now().strftime('%b %d, %Y')}</div>",
        unsafe_allow_html=True,
    )

st.write("")

# ---------- Market summary ----------
st.markdown("### Market snapshot")
indices = [
    ("S&P 500", "^GSPC"),
    ("NASDAQ", "^IXIC"),
    ("DOW JONES", "^DJI"),
    ("RUSSELL 2000", "^RUT"),
]

cols = st.columns(4)
for col, (label, ticker) in zip(cols, indices):
    with col:
        with st.container():
            st.caption(label)
            try:
                quote = get_quote(ticker)
                if quote:
                    price, change, pct = quote
                    st.metric(
                        label="",
                        value=f"{price:,.2f}",
                        delta=f"{change:+,.2f} ({pct:+.2f}%)",
                    )
                else:
                    st.metric(label="", value="Unavailable", delta=None)
            except Exception:
                st.metric(label="", value="Unavailable", delta=None)

st.write("")

# ---------- Main chart and stock details ----------
left, right = st.columns([2.15, 1], gap="large")

with left:
    st.markdown("### Stock performance")

    controls = st.columns([1.4, 1, 1])
    with controls[0]:
        ticker = st.selectbox(
            "Stock",
            ["NVDA", "AAPL", "MSFT", "GOOGL", "AMZN",
             "META", "TSLA", "AMD", "NFLX", "BRK-B"],
            index=0,
        )
    with controls[1]:
        period_label = st.selectbox(
            "Period", ["1D", "5D", "1M", "3M", "6M", "1Y", "5Y"],
            index=3,
        )
    with controls[2]:
        chart_type = st.selectbox(
            "Chart", ["Area", "Line", "Candlestick"]
        )

    period_map = {
        "1D": ("1d", "5m"),
        "5D": ("5d", "15m"),
        "1M": ("1mo", "1d"),
        "3M": ("3mo", "1d"),
        "6M": ("6mo", "1d"),
        "1Y": ("1y", "1d"),
        "5Y": ("5y", "1wk"),
    }

    period, interval = period_map[period_label]
    try:
        history = get_history(ticker, period)

        if not history.empty:
            latest = float(history["Close"].iloc[-1])
            first = float(history["Close"].iloc[0])
            change = latest - first
            pct = change / first * 100 if first else 0

            st.markdown(
                f"<div style='padding:4px 0 12px'>"
                f"<span style='font-size:30px;font-weight:700;color:#f5f7fa'>"
                f"{money(latest)}</span>"
                f"<span style='margin-left:12px;color:{GREEN if change >= 0 else RED}'>"
                f"{change:+.2f} ({pct:+.2f}%)</span></div>",
                unsafe_allow_html=True,
            )
            st.plotly_chart(
                make_chart(history, ticker, chart_type),
                use_container_width=True,
                config={"displayModeBar": False},
            )

            volume = float(history["Volume"].iloc[-1]) if "Volume" in history else 0
            m1, m2, m3 = st.columns(3)
            m1.metric("Period high", money(history["High"].max()))
            m2.metric("Period low", money(history["Low"].min()))
            m3.metric("Latest volume", f"{volume:,.0f}")
        else:
            st.warning("No price history returned. Try another symbol or period.")
    except Exception as exc:
        st.error("Unable to load stock data. Check your internet connection or try again.")
        st.caption(str(exc))

with right:
    st.markdown("### Your watchlist")
    st.caption("Latest available prices")

    for symbol in watchlist:
        try:
            quote = get_quote(symbol)
            if quote:
                price, change, pct = quote
                color = GREEN if pct >= 0 else RED
                st.markdown(
                    f"""
                    <div style="display:flex;justify-content:space-between;
                    align-items:center;padding:15px 12px;margin-bottom:8px;
                    background:#151a22;border:1px solid #272e39;border-radius:12px">
                      <div>
                        <div style="font-weight:700;color:#f3f5f7">{symbol}</div>
                        <div style="font-size:12px;color:#7f8b9d">US equity</div>
                      </div>
                      <div style="text-align:right">
                        <div style="font-weight:600;color:#f3f5f7">${price:,.2f}</div>
                        <div style="font-size:12px;color:{color}">{pct:+.2f}%</div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        except Exception:
            st.caption(f"{symbol} · Quote unavailable")

    st.write("")
    st.markdown("### Quick lookup")
    custom_ticker = st.text_input("Ticker symbol", placeholder="e.g. COST")
    if st.button("Analyze stock", use_container_width=True):
        cleaned = custom_ticker.strip().upper()
        if cleaned:
            st.session_state["selected_ticker"] = cleaned
            st.info(f"Ticker entered: {cleaned}. Select it from the chart selector to view its history.")

# ---------- Market table ----------
st.write("")
st.divider()
st.markdown("### Market movers")
st.caption("Latest available data for popular stocks")

symbols = ["NVDA", "AAPL", "MSFT", "GOOGL", "AMZN",
           "META", "TSLA", "AMD", "NFLX", "JPM"]

rows = []
with st.spinner("Loading market data..."):
    for symbol in symbols:
        try:
            quote = get_quote(symbol)
            if quote:
                price, change, pct = quote
                rows.append({
                    "Ticker": symbol,
                    "Last price": price,
                    "Change": change,
                    "Change (%)": pct,
                })
        except Exception:
            pass

if rows:
    table = pd.DataFrame(rows).sort_values("Change (%)", ascending=False)
    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Ticker": st.column_config.TextColumn("Ticker"),
            "Last price": st.column_config.NumberColumn(
                "Last price", format="$%.2f"
            ),
            "Change": st.column_config.NumberColumn(
                "Change", format="$%+.2f"
            ),
            "Change (%)": st.column_config.NumberColumn(
                "Change (%)", format="%+.2f%%"
            ),
        },
    )
else:
    st.info("Market data is temporarily unavailable. Please try again later.")

st.caption(
    "Stocky UI concept · Market data provided by Yahoo Finance via yfinance. "
    "For informational purposes only; not investment advice."
)