SPCX Market Dashboard

A Streamlit stock dashboard with historical stock charts and a selectable live stock quote and trade monitor powered by Alpaca.

The dashboard also includes a searchable directory of active, non-ETF stock listings across major US exchanges, sourced from Nasdaq Trader. Select a ticker in the chart selector to load its available Yahoo Finance history; the app does not fetch quotes for every listing at once.

The sidebar watchlist can be searched by ticker or company, and stocks can be added from the exchange directory or removed. Changes are saved locally in `watchlist.json` and persist across app restarts; this file is excluded from Git. On a shared deployment, users of the same app instance share this local watchlist.

The **News** workspace polls public RSS feeds from BBC Business, The Guardian Business, NPR Business, the U.S. Securities and Exchange Commission, and the Federal Reserve, and adds headlines from Yahoo Finance's market news search. It checks feeds once per minute, supports source and text filtering, and only displays HTTPS links hosted by the named publisher or Yahoo Finance. Optional AI briefs use OpenAI and require `OPENAI_API_KEY`; news monitoring itself does not require an API key.

The dashboard can automatically refresh stock quotes and chart data every five seconds. Use the **Auto-refresh dashboard (5 sec)** switch in the sidebar to pause or resume it. News feeds are checked once per minute.

The live monitor displays bid and ask prices, a bounded trade tape, estimated trade direction, and large-trade alerts. It runs alongside the existing historical dashboard.

Features

Live Market Data: Streams real-time quotes and trades for the selected stock using Alpaca's IEX data feed.
News Monitoring: Polls publisher and official-source RSS feeds; optional OpenAI summaries are generated from source-attributed headlines and descriptions.
Bid and Ask Monitoring: Displays the latest bid and ask prices along with their respective sizes.
Live Trade Tape: Shows recent trades, including timestamps, prices, share sizes, and estimated trade direction.
Trade Direction Estimation: Classifies trades as buy-initiated, sell-initiated, or uncertain based on the most recently received quote.
Large Trade Alerts: Highlights trades involving 1,000 shares or more.
Real-Time Statistics: Tracks the total number of trades, large trades, and the most recent trade price.
New York Timestamps: Displays trade timestamps in Eastern Time using the America/New_York time zone.
Threaded Data Processing: Runs the market data stream in a background thread while the dashboard remains responsive.
Connection Management: Provides controls to start and stop the feed, along with connection status indicators.
Bounded Trade History: Displays up to 500 recent trades in the trade tape to help maintain UI responsiveness.
Technology Stack

Python 3.10+ — Application logic.
Streamlit — Web dashboard and live monitor.
Pandas and Plotly — Market data tables and interactive charts.
Yahoo Finance via yfinance — Historical dashboard data.
Alpaca Market Data API — Live stock quotes and trades.
alpaca-py — Alpaca's official Python SDK.
Threading and locks — Background streaming and thread-safe monitor state.
zoneinfo — New York time-zone conversion.
Requirements

Before running the application, ensure you have:

Python 3.10 or later.
An Alpaca account with valid API credentials.
Access to the Alpaca stock market data feed.
An internet connection for historical and live market data.
Note: The application explicitly uses the IEX feed. Data availability and subscription permissions depend on your Alpaca account. IEX data may differ from consolidated, all-exchange market data.

Installation

1. Clone the repository


git clone <your-repository-url>
cd <your-project-directory>
Replace the placeholders with your repository URL and project directory.

2. Create a virtual environment


python -m venv .venv
Activate the environment.

Windows — PowerShell


.venv\Scripts\Activate.ps1
Windows — Command Prompt


.venv\Scripts\activate.bat
macOS / Linux


source .venv/bin/activate
3. Install dependencies


python -m pip install --upgrade pip
pip install -r requirements.txt
API Configuration

The application requires two environment variables:

APCA_API_KEY_ID — Your Alpaca API key ID.
APCA_API_SECRET_KEY — Your Alpaca API secret key.
OPENAI_API_KEY — Optional OpenAI API key for AI-generated news briefs.
Obtain your credentials through the official Alpaca website.

Set credentials on Windows

PowerShell:


$env:APCA_API_KEY_ID="your_api_key"
$env:APCA_API_SECRET_KEY="your_api_secret"
Set credentials on macOS / Linux


export APCA_API_KEY_ID="your_api_key"
export APCA_API_SECRET_KEY="your_api_secret"
Replace the example values with your actual credentials.

Security: Never commit API credentials to source control, include them in screenshots, or publish them in your README. Use environment variables or a secure secrets manager.

Running the Application

From the repository root, start the dashboard:


streamlit run src/app_ui.py

The dashboard opens in your browser. In the **Live market monitor** section, search by ticker or company name, select a stock, then click **Switch stock** to connect to that symbol. Changing symbols stops the previous feed and starts a fresh monitor. The monitor updates every two seconds, shows incoming quotes and trades, and marks large trades with `<<< LARGE TRADE`. Click **Stop feed** to end the stream.

Run the automated tests with:


python -m pytest

Dashboard Overview

Connection Status

The dashboard displays the current stream status:

DISCONNECTED — No active stream.
CONNECTING / RECONNECTING — The application is attempting to receive market data.
LIVE — The application has received a quote or trade event.
Stream errors and reconnect attempts are shown in the live monitor.
Bid and Ask Panels

The bid panel displays the latest reported bid price and bid size. The ask panel displays the latest reported ask price and ask size.

Green represents the bid price.
Red represents the ask price.
These values reflect the latest quote updates received by the application.

Live Trade Tape

Each trade is displayed with the following information:


Column	Description
Time (ET)	Trade timestamp in Eastern Time
Symbol	Stock symbol, SPCX
Price	Reported trade price
Shares	Number of shares in the trade
Estimated Side	Heuristic estimate of trade direction
Alert	Large-trade notification, when applicable
The most recent trade appears at the top of the table.

Trade Statistics

The dashboard tracks:

Trades: Total number of trades processed since the application started.
Large trades: Number of trades containing at least 1,000 shares.
Last trade: Price of the most recently processed trade.
The counters are maintained in memory and reset when the application is restarted.

Large Trade Detection

A trade is classified as a large trade when its share size is greater than or equal to the configured threshold:


LARGE_TRADE_SHARES = 1_000
For example:


Trade Size	Classification
100 shares	Normal trade
999 shares	Normal trade
1,000 shares	Large trade
5,000 shares	Large trade
Large trades are identified by the alert `<<< LARGE TRADE` in the trade tape.

You can change the threshold by modifying LARGE_TRADE_SHARES in the source code.

Trade Direction Estimation

The application estimates trade direction by comparing each trade's price with the most recently received quote.


Condition	Classification
Trade price is at or above the ask	BUY-INITIATED (EST.)
Trade price is at or below the bid	SELL-INITIATED (EST.)
Trade price falls between bid and ask	MID-SPREAD / UNCERTAIN
No quote is available	UNKNOWN
Important: These classifications are estimates, not confirmed buyer or seller identities. Quotes can change between quote and trade events, and trades may execute inside or outside the displayed spread.

Project Structure


Quick-/
├── src/
│   ├── app_ui.py        # Streamlit dashboard
│   ├── live_monitor.py  # Thread-safe live quote/trade state
│   └── market_data.py   # Alpaca stream and reconnect handling
├── Tests/               # Automated tests
├── requirements.txt
└── README.md

Troubleshooting

Missing API credentials

Problem: A dialog reports that API credentials are missing.

Solution: Set both APCA_API_KEY_ID and APCA_API_SECRET_KEY in the same terminal or environment used to launch Python.

Connection or authentication errors

Problem: The stream reports an error or fails to connect.

Solution:

Verify that your API key and secret are correct.
Confirm that your account has access to the requested data feed.
Check your network connection.
Review the error message returned by Alpaca.
No quotes or trades appear

Problem: The connection appears active, but the dashboard does not update.

Solution:

Verify that the symbol is valid and supported by your Alpaca data subscription.
Confirm that market data is available for the symbol.
Remember that the code subscribes specifically to the IEX feed.
Check whether the market is open and whether trades are occurring.
Dashboard dependencies are missing

Problem: Streamlit or another package cannot be imported.

Solution: Install dependencies from the repository root with `python -m pip install -r requirements.txt`.

The live feed does not start

Problem: The live monitor shows a credential or connection error.

Solution: Set `APCA_API_KEY_ID` and `APCA_API_SECRET_KEY` in the environment used to launch Streamlit, verify the feed subscription, and review the error shown in the monitor.

Limitations and Considerations

The live monitor subscribes to one selected symbol at a time using Alpaca's IEX feed, not consolidated all-exchange data. Symbol coverage and access depend on Alpaca account permissions.
Trade direction is estimated using the latest available quote and is not a definitive classification.
Trade history and counters are stored in memory and are not persisted to disk.
The dashboard limits the visible trade tape to 500 entries.
The live stream retries unexpected disconnects with exponential backoff; historical data backfilling is not implemented.
A displayed LIVE status does not guarantee that every market event is received without delay or interruption.
Disclaimer

This project is intended for market data visualization, educational use, and research purposes. It does not provide investment advice or execute trades.

Market data may be delayed, incomplete, or different from other market data sources. Do not use the displayed trade classifications or alerts as the sole basis for financial decisions.

Resources

Alpaca Developer Documentation
Alpaca Python SDK — alpaca-py
Python Documentation
Streamlit Documentation
Plotly Documentation
yfinance Documentation
License

No license has been specified yet. Add a license file if you intend to distribute this project or allow others to reuse its code.
