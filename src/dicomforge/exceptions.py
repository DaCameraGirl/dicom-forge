"""Typed exception hierarchy for dicom-forge.

A single base (:class:`DicomForgeError`) lets callers catch every library-raised
error with one ``except`` while still allowing fine-grained handling. Every error
carries a human-readable message; subclasses add structured context where useful.
"""

from __future__ import annotations


class DicomForgeError(Exception):
    """Base class for all errors raised by dicom-forge."""


class IngestionError(DicomForgeError):
    """Raised when a DICOM source cannot be discovered, read, or parsed."""


class EmptySeriesError(IngestionError):
    """Raised when a path contains no readable DICOM instances for a series."""


class DeidentificationError(DicomForgeError):
    """Raised when de-identification cannot satisfy the requested profile."""


class ConversionError(DicomForgeError):
    """Raised when a volume cannot be written to the requested output format."""


class MissingDependencyError(DicomForgeError):
    """Raised when an optional dependency required for an operation is absent.

    The message names the missing package and the extra that installs it so the
    failure is actionable rather than a bare ``ImportError`` deep in a call stack.
    """

    def __init__(self, package: str, extra: str) -> None:
        super().__init__(
            f"'{package}' is required for this operation but is not installed. "
            f"Install it with:  pip install 'dicom-forge[{extra}]'"
        )
        self.package = package
        self.extra = extra


class QualityControlError(DicomForgeError):
    """Raised when a QC gate is configured to fail hard and the series fails it."""
