import logging
from typing import Any, cast
from flask import Flask


# Add color constants
class LogColors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    WARNING = "\033[93m"
    DANGER = "\033[91m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colored output"""

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)

        # Add color based on logger name or custom attributes
        if hasattr(record, "subscription"):
            return f"{LogColors.CYAN}[SUBSCRIPTION]{LogColors.RESET} {message}"
        elif hasattr(record, "payment"):
            return f"{LogColors.BLUE}[PAYMENT]{LogColors.RESET} {message}"

        # Color based on log level
        if record.levelno >= logging.ERROR:
            return f"{LogColors.DANGER}{message}{LogColors.RESET}"
        elif record.levelno >= logging.WARNING:
            return f"{LogColors.WARNING}{message}{LogColors.RESET}"
        elif record.levelno >= logging.INFO:
            return f"{LogColors.GREEN}{message}{LogColors.RESET}"

        return message


# Add this to the existing get_logger function
def get_logger(name: str, **kwargs: Any) -> logging.Logger:
    """Returns a Logger instance"""
    # Initialize the logger
    logger = logging.getLogger(name)

    # Configure logger if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    # Add colored formatter to the console handler
    for log_handler in logger.handlers:
        log_handler = cast(logging.Handler, log_handler)
        if isinstance(log_handler, logging.StreamHandler):
            log_handler.setFormatter(ColoredFormatter("%(asctime)s:%(levelname)s:%(name)s:%(message)s"))

    return logger


def setup_colored_logging(app: Flask) -> Flask:
    """Apply colored logging to a Flask app"""
    # Clear existing handlers
    app.logger.handlers.clear()

    # Add a new handler with our colored formatter
    handler = logging.StreamHandler()
    handler.setFormatter(ColoredFormatter("%(asctime)s:%(levelname)s:%(name)s:%(message)s"))
    app.logger.addHandler(handler)

    # Set the logger level and prevent propagation
    app.logger.setLevel(logging.INFO)
    app.logger.propagate = False

    return app
