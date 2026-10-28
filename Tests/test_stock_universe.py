import pandas as pd
import pytest

from src.stock_universe import _active_stocks


def test_active_stocks_excludes_funds_and_test_issues():
    listings = pd.DataFrame({
        "Symbol": ["AAA", "FUND", "TEST"],
        "Security Name": ["Example Corp", "Example Fund", "Test Corp"],
        "ETF": ["N", "Y", "N"],
        "Test Issue": ["N", "N", "Y"],
    })

    result = _active_stocks(
        listings,
        symbol_column="Symbol",
        exchange_column="",
    )

    assert result.to_dict("records") == [{
        "Ticker": "AAA",
        "Company": "Example Corp",
        "Exchange": "NASDAQ",
    }]


def test_active_stocks_rejects_unexpected_directory_format():
    with pytest.raises(ValueError, match="missing expected columns"):
        _active_stocks(
            pd.DataFrame({"Symbol": ["AAA"]}),
            symbol_column="Symbol",
            exchange_column="",
        )


def test_active_stocks_maps_other_exchange_names():
    listings = pd.DataFrame({
        "ACT Symbol": ["AAA"],
        "Security Name": ["Example Corp"],
        "ETF": ["N"],
        "Test Issue": ["N"],
        "Exchange": ["F"],
    })

    result = _active_stocks(
        listings,
        symbol_column="ACT Symbol",
        exchange_column="Exchange",
        exchange_names={"F": "Other US listing"},
    )

    assert result.loc[0, "Exchange"] == "Other US listing"
