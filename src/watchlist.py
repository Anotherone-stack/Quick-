"""Local persistence helpers for the dashboard watchlist."""

import json
import os
import tempfile
from pathlib import Path


DEFAULT_WATCHLIST = ["AAPL", "NVDA", "MSFT", "GOOGL", "AMZN"]
WATCHLIST_PATH = Path(__file__).resolve().parent.parent / "watchlist.json"


def _normalize_symbols(symbols: list[str]) -> list[str]:
    if not isinstance(symbols, list) or any(
        not isinstance(symbol, str) for symbol in symbols
    ):
        raise ValueError("The watchlist must be a list of stock symbols.")

    return list(dict.fromkeys(
        symbol.strip().upper() for symbol in symbols if symbol.strip()
    ))


def load_watchlist(path: Path = WATCHLIST_PATH) -> list[str]:
    """Load saved symbols, using the starter watchlist if none is saved."""
    try:
        contents = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return DEFAULT_WATCHLIST.copy()

    try:
        symbols = json.loads(contents)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Unable to read saved watchlist at {path}.") from exc

    return _normalize_symbols(symbols)


def save_watchlist(symbols: list[str], path: Path = WATCHLIST_PATH) -> None:
    """Atomically save a normalized list of stock symbols."""
    normalized = _normalize_symbols(symbols)
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(normalized, temporary_file, indent=2)
            temporary_file.write("\n")
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
