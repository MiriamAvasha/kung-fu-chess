import logging
from pathlib import Path
from typing import Optional


LOG_DIR = Path(__file__).resolve().parents[2] / 'logs'


def setup_activity_logger(
    name: str,
    filename: str,
    level: int = logging.INFO,
    console: bool = False,
) -> logging.Logger:
    """Return a named logger that writes activity lines to logs/<filename>."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    logger.propagate = False

    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    file_handler = logging.FileHandler(
        LOG_DIR / filename,
        encoding='utf-8',
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if console:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
    return logger


def log_activity(
    logger: logging.Logger,
    direction: str,
    payload: str,
    peer: Optional[str] = None,
):
    if peer:
        logger.info('%s %s | %s', direction, peer, payload)
    else:
        logger.info('%s | %s', direction, payload)
