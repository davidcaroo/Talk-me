import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from utils.paths import get_logs_dir

LOGGER_NAME = "VoiceDictation"
LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    log_file: Path | str | None = None,
    level: int = logging.INFO,
    name: str = LOGGER_NAME
) -> logging.Logger:
    """Configures structured console and rotating file logging."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Rotating File Handler
    if log_file is None:
        target_log_file = get_logs_dir() / "app.log"
    else:
        target_log_file = Path(log_file)
        target_log_file.parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        filename=target_log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def get_logger(name: str = LOGGER_NAME) -> logging.Logger:
    """Returns an existing logger or initializes it if not yet configured."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logging(name=name)
    return logger


# Alias for compatibility
setup_logger = setup_logging
