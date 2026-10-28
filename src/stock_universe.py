"""Helpers for loading the current US-listed stock symbol directory."""

import pandas as pd


NASDAQ_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"

OTHER_EXCHANGES = {
    "A": "NYSE American",
    "F": "Other US listing",
    "N": "NYSE",
    "P": "NYSE Arca",
    "V": "IEX",
    "Z": "Cboe BZX",
}


def _validate_columns(data: pd.DataFrame, required: set[str]) -> None:
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(
            "The stock directory response is missing expected columns: "
            + ", ".join(sorted(missing))
        )


def _active_stocks(
    data: pd.DataFrame,
    symbol_column: str,
    exchange_column: str,
    exchange_names: dict[str, str] | None = None,
) -> pd.DataFrame:
    _validate_columns(data, {symbol_column, "Security Name", "ETF", "Test Issue"})
    active = data.loc[
        data["ETF"].eq("N") & data["Test Issue"].eq("N"),
        [symbol_column, "Security Name", *([exchange_column] if exchange_column else [])],
    ].copy()
    active["Ticker"] = active[symbol_column].astype(str).str.strip()
    active["Company"] = active["Security Name"].astype(str).str.strip()
    if exchange_column:
        active["Exchange"] = active[exchange_column].map(exchange_names or {}).fillna(
            active[exchange_column]
        )
    else:
        active["Exchange"] = "NASDAQ"
    return active.loc[
        active["Ticker"].ne("") & active["Ticker"].ne("nan"),
        ["Ticker", "Company", "Exchange"],
    ]


def load_us_stock_universe() -> pd.DataFrame:
    """Load active non-ETF stocks listed on US exchanges from Nasdaq Trader."""
    nasdaq = pd.read_csv(NASDAQ_LISTED_URL, sep="|", dtype=str)
    other = pd.read_csv(OTHER_LISTED_URL, sep="|", dtype=str)

    nasdaq_stocks = _active_stocks(
        nasdaq,
        symbol_column="Symbol",
        exchange_column="",
    )
    other_stocks = _active_stocks(
        other,
        symbol_column="ACT Symbol",
        exchange_column="Exchange",
        exchange_names=OTHER_EXCHANGES,
    )

    return (
        pd.concat([nasdaq_stocks, other_stocks], ignore_index=True)
        .drop_duplicates(subset="Ticker")
        .sort_values("Ticker", kind="stable")
        .reset_index(drop=True)
    )
