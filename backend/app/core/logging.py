"""Application logging configuration."""

import logging
import sys

TRACE_LEVEL = 5
logging.addLevelName(TRACE_LEVEL, "TRACE")


def _trace(self: logging.Logger, message: str, *args: object, **kwargs: object) -> None:
    """Log a TRACE-level message when the logger is TRACE-enabled."""
    if self.isEnabledFor(TRACE_LEVEL):
        self.log(TRACE_LEVEL, message, *args, **kwargs)


logging.Logger.trace = _trace  # type: ignore[attr-defined]


def configure_logging(level: str = "INFO") -> None:
    """Configure basic logging for the application."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )

    root = logging.getLogger()
    root.setLevel(log_level)
    root.handlers.clear()
    root.addHandler(handler)


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a configured logger."""
    return logging.getLogger(name or __name__)
