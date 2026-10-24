
import logging
import logging.handlers
import os
from pathlib import Path


DEFAULT_LOG_DIR = Path("logs")
DEFAULT_LOG_FILE = "market_app.log"

LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | "
    "%(name)s | %(message)s"
)
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    log_level: str | None = None,
    log_dir: str | Path = DEFAULT_LOG_DIR,
    log_file: str = DEFAULT_LOG_FILE,
    console: bool = True,
) -> logging.Logger:
    """
    Configure application-wide logging.

    Returns the root application logger.
    Safe to call repeatedly without duplicating handlers.
    """
    level_name = (
        log_level
        or os.getenv("LOG_LEVEL", "INFO")
    ).upper()

    level = getattr(logging, level_name, None)
    if not isinstance(level, int):
        raise ValueError(
            f"Invalid logging level: {level_name}"
        )

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("market_app")
    logger.setLevel(level)
    logger.propagate = False

    formatter = logging.Formatter(
        fmt=LOG_FORMAT,
        datefmt=DATE_FORMAT,
    )

    # Avoid adding duplicate handlers on repeated setup.
    if not getattr(logger, "_market_logging_configured", False):
        file_handler = logging.handlers.RotatingFileHandler(
            log_path / log_file,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        if console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        logger._market_logging_configured = True

    # Update handler levels when configuration changes.
    for handler in logger.handlers:
        handler.setLevel(level)

    return logger
