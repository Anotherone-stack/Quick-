
"""CSV export utilities for timestamped market trades."""

import csv
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Mapping


COLUMNS = (
    "trade_id",
    "timestamp",
    "symbol",
    "side",
    "price",
    "quantity",
)


def _format_timestamp(value) -> str:
    """Normalize a datetime or Unix timestamp to ISO 8601 UTC."""
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            raise ValueError("Naive timestamps are not supported")
        dt = dt.astimezone(timezone.utc)
    elif isinstance(value, (int, float, Decimal)) and not isinstance(
        value, bool
    ):
        dt = datetime.fromtimestamp(float(value), tz=timezone.utc)
    else:
        raise ValueError("timestamp must be an aware datetime or Unix time")

    return dt.isoformat(timespec="microseconds").replace("+00:00", "Z")


def export_trades(
    trades: Iterable[Mapping],
    output_path: str | os.PathLike,
) -> int:
    """Write trades to CSV and return the number of exported rows.

    Required fields: timestamp, symbol, side, price, quantity.
    trade_id is optional.
    """
    path = Path(output_path)
    count = 0

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=COLUMNS,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()

        for trade in trades:
            missing = {
                "timestamp", "symbol", "side", "price", "quantity"
            } - trade.keys()
            if missing:
                raise ValueError(
                    f"Trade is missing required fields: {sorted(missing)}"
                )

            row = dict(trade)
            row["timestamp"] = _format_timestamp(row["timestamp"])

            # Preserve exact decimal values when supplied as Decimal.
            for key in ("price", "quantity"):
                value = row[key]
                if isinstance(value, bool) or value is None:
                    raise ValueError(f"Invalid {key}")
                if isinstance(value, Decimal):
                    if not value.is_finite():
                        raise ValueError(f"Invalid {key}")
                    row[key] = format(value, "f")
                elif isinstance(value, (int, float)):
                    if not (
                        value == value
                        and value not in (float("inf"), float("-inf"))
                    ):
                        raise ValueError(f"Invalid {key}")
                    row[key] = str(value)
                else:
                    raise ValueError(f"Invalid {key}")

            writer.writerow({key: row.get(key, "") for key in COLUMNS})
            count += 1

    return count
