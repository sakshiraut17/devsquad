import logging
import sys
from app.core.config import settings


def setup_logging() -> logging.Logger:
    """Configure structured logging for DevSquad FastAPI application."""
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    logger = logging.getLogger("devsquad")
    logger.setLevel(log_level)
    return logger


logger = setup_logging()
