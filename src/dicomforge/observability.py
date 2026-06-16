"""Structured, dependency-light logging for dicom-forge.

We deliberately avoid pulling a logging framework. The standard library plus Rich
(already a CLI dependency) gives colourised console logs interactively and clean,
parseable logs in CI. Library code should call :func:`get_logger`; only the CLI
entry point should call :func:`configure_logging`, so importing the library never
mutates the root logger of a host application (e.g. 3D Slicer).
"""

from __future__ import annotations

import logging
from typing import Literal

from rich.logging import RichHandler

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

_CONFIGURED = False


def configure_logging(level: LogLevel = "INFO", *, rich: bool = True) -> None:
    """Configure the ``dicomforge`` logger namespace.

    Idempotent: calling it more than once will not attach duplicate handlers.
    Only application entry points (the CLI) should call this.
    """
    global _CONFIGURED
    logger = logging.getLogger("dicomforge")
    logger.setLevel(level)
    if _CONFIGURED:
        return

    handler: logging.Handler
    if rich:
        handler = RichHandler(rich_tracebacks=True, show_path=False, markup=False)
        handler.setFormatter(logging.Formatter("%(message)s", datefmt="[%X]"))
    else:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    _CONFIGURED = True


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a child logger under the ``dicomforge`` namespace.

    Passing ``__name__`` from a submodule yields ``dicomforge.<module>`` loggers
    that all inherit the configuration applied by :func:`configure_logging`.
    """
    if name is None or name == "dicomforge":
        return logging.getLogger("dicomforge")
    suffix = name.split("dicomforge.", 1)[-1]
    return logging.getLogger(f"dicomforge.{suffix}")
