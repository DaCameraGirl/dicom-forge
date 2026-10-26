"""Typed exception hierarchy for dicom-forge.

A single base (:class:`DicomForgeError`) lets callers catch every library-raised
error with one ``except`` while still allowing fine-grained handling. Every error
carries a human-readable message; subclasses add structured context where useful.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # models imports nothing from here, but keep the runtime import-free
    from .models import PixelPrivacyReport


class DicomForgeError(Exception):
    """Base class for all errors raised by dicom-forge."""


class ConfigurationError(DicomForgeError, ValueError):
    """Raised for an invalid setting, e.g. an unsafe pseudonymisation secret.

    Also a ``ValueError``, so existing ``except ValueError`` handlers and pydantic
    validators keep working.
    """


class IngestionError(DicomForgeError):
    """Raised when a DICOM source cannot be discovered, read, or parsed."""


class EmptySeriesError(IngestionError):
    """Raised when a path contains no readable DICOM instances for a series."""


class DeidentificationError(DicomForgeError):
    """Raised when de-identification cannot satisfy the requested profile."""


class BurnedInAnnotationError(DeidentificationError):
    """Raised when a series is known or suspected to carry burned-in pixel annotation.

    Pixel data is never de-identified, so such series are rejected before anything is
    written unless the caller explicitly opts in. The message carries only reason codes
    and counts, never paths, UIDs or attribute values. ``report`` holds the structured
    :class:`~dicomforge.models.PixelPrivacyReport` for callers that need the reasons.
    """

    def __init__(self, message: str, report: PixelPrivacyReport | None = None) -> None:
        super().__init__(message)
        self.report = report


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
            f"Install it with:  pip install 'dicom-anvil[{extra}]'"
        )
        self.package = package
        self.extra = extra


class QualityControlError(DicomForgeError):
    """Raised when a QC gate is configured to fail hard and the series fails it."""
