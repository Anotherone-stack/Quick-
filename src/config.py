import os

SYMBOL = os.getenv("SPCX_SYMBOL", "SPCX")
LARGE_TRADE_SHARES = int(
    os.getenv("LARGE_TRADE_SHARES", "1000")
)
DATA_FEED = os.getenv("SPCX_DATA_FEED", "iex")
MAX_TAPE_ROWS = 500