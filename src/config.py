# Import Python's built-in os module to access environment variables.
import os

# Set the stock symbol using the SPCX_SYMBOL environment variable.
# If the variable is not set, use "SPCX" as the default symbol.
SYMBOL = os.getenv("SPCX_SYMBOL", "SPCX")

# Set the minimum number of shares that qualifies as a large trade.
# Read the value from the LARGE_TRADE_SHARES environment variable.
# If the variable is not set, use "1000" as the default.
# Convert the environment variable's string value into an integer.
LARGE_TRADE_SHARES = int(
    os.getenv("LARGE_TRADE_SHARES", "1000")
)

# Select the market data feed using the SPCX_DATA_FEED environment variable.
# If the variable is not set, default to the "iex" feed.
DATA_FEED = os.getenv("SPCX_DATA_FEED", "iex")

# Set the maximum number of rows to retain in the trade tape to 500.
MAX_TAPE_ROWS = 500