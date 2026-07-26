from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from app.config import LOG_DIR


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("xhs_ecom")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(
        LOG_DIR / "application.log",
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    logger.addHandler(handler)
    return logger
