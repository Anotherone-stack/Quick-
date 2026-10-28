import json

import pytest

from src.watchlist import DEFAULT_WATCHLIST, load_watchlist, save_watchlist


def test_load_watchlist_uses_defaults_when_no_file_exists(tmp_path):
    assert load_watchlist(tmp_path / "watchlist.json") == DEFAULT_WATCHLIST


def test_save_and_load_watchlist_normalizes_and_deduplicates(tmp_path):
    path = tmp_path / "watchlist.json"

    save_watchlist([" aapl ", "NVDA", "AAPL"], path)

    assert load_watchlist(path) == ["AAPL", "NVDA"]


def test_load_watchlist_reports_invalid_json(tmp_path):
    path = tmp_path / "watchlist.json"
    path.write_text("{invalid", encoding="utf-8")

    with pytest.raises(ValueError, match="Unable to read saved watchlist"):
        load_watchlist(path)


def test_load_watchlist_rejects_invalid_data(tmp_path):
    path = tmp_path / "watchlist.json"
    path.write_text(json.dumps({"symbol": "AAPL"}), encoding="utf-8")

    with pytest.raises(ValueError, match="must be a list"):
        load_watchlist(path)
