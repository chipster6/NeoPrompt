from __future__ import annotations
import logging
import sys
from pythonjsonlogger import jsonlogger


def configure_logging(level: str = "INFO") -> None:
    """Configure structured JSON logging for app and uvicorn.

    - Root logger outputs JSON to stdout
    - Uvicorn loggers inherit same formatter
    """
    lvl = getattr(logging, level.upper(), logging.INFO)
    logger = logging.getLogger()
    logger.setLevel(lvl)

    # Clear existing handlers to avoid duplicate logs
    for h in list(logger.handlers):
        logger.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    fmt = jsonlogger.JsonFormatter("%(levelname)s %(name)s %(message)s %(asctime)s %(module)s %(funcName)s %(lineno)d")
    handler.setFormatter(fmt)
    logger.addHandler(handler)

    # Tweak uvicorn loggers
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers = [handler]
        lg.setLevel(lvl)
