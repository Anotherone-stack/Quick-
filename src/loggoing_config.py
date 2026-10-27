
# Import Python's built-in logging module to record application events.
import logging

# Import logging.handlers to access features such as rotating log files.
import logging.handlers

# Import os to read environment variables from the operating system.
import os

# Import Path to create, manage, and manipulate file-system paths.
from pathlib import Path


# Set the default directory where log files will be stored.
DEFAULT_LOG_DIR = Path("logs")

# Set the default name of the application's log file.
DEFAULT_LOG_FILE = "market_app.log"

# Define the format used for each log message.
# Include the timestamp, log level, logger name, and message text.
# The line break inside the string joins the two pieces into one format string.
LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | "
    "%(name)s | %(message)s"
)

# Define the format used to display timestamps in log messages.
# Example: 2026-10-27 14:30:00.
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# Define a function to configure logging for the application.
def setup_logging(
    log_level: str | None = None,  # Optional logging level, such as INFO or DEBUG.
    log_dir: str | Path = DEFAULT_LOG_DIR,  # Directory in which to save log files.
    log_file: str = DEFAULT_LOG_FILE,  # Name of the log file to create.
    console: bool = True,  # Decide whether log messages should also appear in the console.
) -> logging.Logger:  # Specify that the function returns a Logger object.

    # Document the purpose and behavior of this function.
    """
    Configure application-wide logging.

    Returns the root application logger.
    Safe to call repeatedly without duplicating handlers.
    """

    # Choose the explicitly supplied log level if present.
    # Otherwise, read LOG_LEVEL from the environment, defaulting to INFO.
    # Convert the selected level name to uppercase.
    level_name = (
        log_level
        or os.getenv("LOG_LEVEL", "INFO")
    ).upper()

    # Look up the corresponding logging constant, such as logging.INFO.
    # Return None if the supplied name is not a valid logging attribute.
    level = getattr(logging, level_name, None)

    # Check that the resolved level is an integer.
    # Python's standard logging levels are represented by integers.
    if not isinstance(level, int):

        # Stop setup and report the invalid logging level.
        raise ValueError(
            f"Invalid logging level: {level_name}"
        )

    # Convert the supplied log directory into a Path object.
    log_path = Path(log_dir)

    # Create the log directory if it does not already exist.
    # Create any missing parent directories as well.
    # exist_ok=True prevents an error if the directory already exists.
    log_path.mkdir(parents=True, exist_ok=True)

    # Retrieve the application's named logger or create it if necessary.
    logger = logging.getLogger("market_app")

    # Set the minimum severity level this logger will process.
    logger.setLevel(level)

    # Prevent messages from propagating to the root logger.
    # This helps avoid duplicate output from separately configured root handlers.
    logger.propagate = False

    # Create a formatter that controls how log records are displayed.
    formatter = logging.Formatter(
        fmt=LOG_FORMAT,  # Apply the previously defined message format.
        datefmt=DATE_FORMAT,  # Apply the previously defined timestamp format.
    )

    # Avoid adding duplicate handlers when setup_logging is called repeatedly.
    # Check whether this logger has already been configured by this function.
    if not getattr(logger, "_market_logging_configured", False):

        # Create a rotating file handler that writes log messages to a file.
        file_handler = logging.handlers.RotatingFileHandler(
            log_path / log_file,  # Combine the directory and file name.
            maxBytes=5 * 1024 * 1024,  # Rotate the file when it reaches 5 MiB.
            backupCount=5,  # Keep up to five rotated backup log files.
            encoding="utf-8",  # Encode log text using UTF-8.
        )

        # Set the minimum severity level for messages written to the file.
        file_handler.setLevel(level)

        # Apply the chosen message format to the file handler.
        file_handler.setFormatter(formatter)

        # Attach the file handler to the application logger.
        logger.addHandler(file_handler)

        # Check whether console logging is enabled.
        if console:

            # Create a handler that writes log messages to the console.
            console_handler = logging.StreamHandler()

            # Set the minimum severity level for console messages.
            console_handler.setLevel(level)

            # Apply the chosen message format to console messages.
            console_handler.setFormatter(formatter)

            # Attach the console handler to the application logger.
            logger.addHandler(console_handler)

        # Mark the logger as configured to avoid adding duplicate handlers.
        logger._market_logging_configured = True

    # Update the severity level of every existing handler.
    # This allows a repeated setup call to change the logging level.
    for handler in logger.handlers:

        # Apply the current logging level to this handler.
        handler.setLevel(level)

    # Return the configured logger so other modules can use it.
    return logger
