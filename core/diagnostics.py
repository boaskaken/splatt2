"""Bounded runtime logs and exception reporting."""
import logging
from logging.handlers import RotatingFileHandler
import sys
import threading

from core.paths import user_data_dir


def setup_logging():
    path = user_data_dir() / "splatt2.log"
    logger = logging.getLogger()
    if not any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
        handler = RotatingFileHandler(path, maxBytes=1_000_000, backupCount=3,
                                      encoding="utf-8")
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    def worker_error(args):
        logger.error("Unhandled worker error: %s", args.thread.name,
                     exc_info=(args.exc_type, args.exc_value, args.exc_traceback))
    threading.excepthook = worker_error
    logger.info("Starting Splatt2; Python %s", sys.version.split()[0])
    return path
