
# Describe the purpose of this module.
"""CSV export utilities for timestamped market trades."""

# Import Python's built-in CSV module for writing CSV files.
import csv

# Import os to support operating-system path types.
import os

# Import datetime to work with dates and times.
# Import timezone to convert timestamps to Coordinated Universal Time (UTC).
from datetime import datetime, timezone

# Import Decimal to handle precise decimal numbers, such as financial prices.
from decimal import Decimal

# Import Path to work with file paths in a convenient, cross-platform way.
from pathlib import Path

# Import Iterable for type hints describing collections of items.
# Import Mapping for type hints describing dictionary-like objects.
from typing import Iterable, Mapping


# Define the column names and their order in the exported CSV file.
COLUMNS = (
    "trade_id",   # Store the unique identifier for a trade, if available.
    "timestamp",  # Store the date and time when the trade occurred.
    "symbol",     # Store the ticker symbol of the traded asset.
    "side",       # Store the trade side, such as buy or sell, if provided.
    "price",      # Store the price at which the asset was traded.
    "quantity",   # Store the number of shares or units traded.
)


# Define a helper function to convert timestamps into a consistent format.
# Accept a datetime object or a Unix timestamp and return a string.
def _format_timestamp(value) -> str:

    # Describe the purpose of the function.
    """Normalize a datetime or Unix timestamp to ISO 8601 UTC."""

    # Check whether the supplied value is a datetime object.
    if isinstance(value, datetime):

        # Store the supplied datetime in a local variable.
        dt = value

        # Check whether the datetime lacks timezone information.
        if dt.tzinfo is None:

            # Reject timestamps without timezone information.
            raise ValueError("Naive timestamps are not supported")

        # Convert the timezone-aware datetime to UTC.
        dt = dt.astimezone(timezone.utc)

    # Otherwise, check whether the value is a number or Decimal.
    # Exclude booleans because Python treats bool as a subclass of int.
    elif isinstance(value, (int, float, Decimal)) and not isinstance(
        value, bool
    ):

        # Interpret the number as Unix time in seconds and convert it to UTC.
        dt = datetime.fromtimestamp(float(value), tz=timezone.utc)

    # Reject any value that is neither a supported datetime nor Unix timestamp.
    else:
        raise ValueError("timestamp must be an aware datetime or Unix time")

    # Format the timestamp using ISO 8601 with six fractional-second digits.
    # Replace the UTC offset "+00:00" with "Z" to indicate UTC explicitly.
    return dt.isoformat(timespec="microseconds").replace("+00:00", "Z")


# Define a function that exports a collection of trades to a CSV file.
# Each trade is expected to be a dictionary-like mapping.
# Accept either a string path or an operating-system-compatible path object.
# Return an integer representing the number of exported trade rows.
def export_trades(
    trades: Iterable[Mapping],
    output_path: str | os.PathLike,
) -> int:

    # Describe the function and document its required fields.
    """Write trades to CSV and return the number of exported rows.

    Required fields: timestamp, symbol, side, price, quantity.
    trade_id is optional.
    """

    # Convert the supplied output path into a Path object.
    path = Path(output_path)

    # Initialize a counter for the number of exported trades.
    count = 0

    # Open the output file in write mode.
    # Use UTF-8 encoding to support standard text characters.
    # Set newline="" so the CSV module can manage line endings correctly.
    with path.open("w", encoding="utf-8", newline="") as file:

        # Create a CSV dictionary writer that maps dictionary keys to columns.
        writer = csv.DictWriter(
            file,  # Write to the opened output file.
            fieldnames=COLUMNS,  # Use the predefined column names and order.
            extrasaction="ignore",  # Ignore dictionary keys not listed in COLUMNS.
            lineterminator="\n",  # End each CSV row with a newline character.
        )

        # Write the column names as the first row of the CSV file.
        writer.writeheader()

        # Process each trade supplied to the export function.
        for trade in trades:

            # Identify required fields that are missing from the trade.
            # Subtract the available dictionary keys from the required field set.
            missing = {
                "timestamp", "symbol", "side", "price", "quantity"
            } - trade.keys()

            # Check whether any required fields are missing.
            if missing:

                # Stop processing and report the names of missing fields.
                raise ValueError(
                    f"Trade is missing required fields: {sorted(missing)}"
                )

            # Copy the trade into a regular dictionary.
            # This allows the export process to modify values without changing
            # the original trade mapping.
            row = dict(trade)

            # Convert the trade timestamp into a consistent UTC string.
            row["timestamp"] = _format_timestamp(row["timestamp"])

            # Preserve exact decimal values when supplied as Decimal.
            # Process the price and quantity fields separately.
            for key in ("price", "quantity"):

                # Retrieve the current price or quantity value.
                value = row[key]

                # Reject booleans and missing values for financial fields.
                if isinstance(value, bool) or value is None:

                    # Raise an error identifying the invalid field.
                    raise ValueError(f"Invalid {key}")

                # Check whether the value is a Decimal instance.
                if isinstance(value, Decimal):

                    # Reject Decimal values such as NaN and infinity.
                    if not value.is_finite():

                        # Raise an error for a non-finite decimal value.
                        raise ValueError(f"Invalid {key}")

                    # Convert the Decimal to a string without losing its
                    # represented decimal precision through a float conversion.
                    row[key] = format(value, "f")

                # Otherwise, accept integer or floating-point values.
                elif isinstance(value, (int, float)):

                    # Verify that the number is not NaN or positive/negative infinity.
                    # NaN is detected because it is not equal to itself.
                    if not (
                        value == value
                        and value not in (float("inf"), float("-inf"))
                    ):

                        # Raise an error if the number is not finite.
                        raise ValueError(f"Invalid {key}")

                    # Convert the number to a string for CSV output.
                    row[key] = str(value)

                # Reject values that are not supported numeric types.
                else:

                    # Raise an error identifying the invalid field.
                    raise ValueError(f"Invalid {key}")

            # Write the trade as a CSV row.
            # Include only the predefined columns and use an empty string
            # when an optional field, such as trade_id, is not provided.
            writer.writerow({key: row.get(key, "") for key in COLUMNS})

            # Increase the exported trade counter by one.
            count += 1

    # Return the total number of rows written.
    return count
