"""DICOM ingestion: discover instances, group into series, assemble volumes.

This module is pure pydicom + numpy so it works in any environment (including a
3D Slicer Python console) without native ITK libraries. The central object is
:class:`DicomSeries`, which couples the ordered pydicom datasets with a lazily
built voxel volume and validated :class:`~dicomforge.models.SeriesMetadata`.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Iterator
from pathlib import Path

import numpy as np
import pydicom
from pydicom.dataset import FileDataset

from .exceptions import EmptySeriesError, IngestionError
from .models import SeriesMetadata
from .observability import get_logger

logger = get_logger(__name__)

# Tags that mark a dataset as actual image data we can stack into a volume.
_PIXEL_TAG = 0x7FE00010


def iter_dicom_files(root: str | Path) -> Iterator[Path]:
    """Yield candidate DICOM file paths under ``root`` (recursively).

    Accepts a single file or a directory. Files are *not* parsed here; we only
    filter obvious non-DICOM (directories, zero-byte files). A single root may
    contain several studies/series; grouping happens in :func:`load_series`.
    """
    root_path = Path(root)
    if not root_path.exists():
        raise IngestionError(f"Path does not exist: {root_path}")
    if root_path.is_file():
        yield root_path
        return
    for path in sorted(root_path.rglob("*")):
        if path.is_file() and path.stat().st_size > 0 and path.name != "DICOMDIR":
            yield path


def _safe_read(path: Path) -> FileDataset | None:
    """Read a dataset, returning None for files that are not valid DICOM."""
    try:
        return pydicom.dcmread(path, force=False)
    except (pydicom.errors.InvalidDicomError, OSError, ValueError):
        logger.debug("Skipping non-DICOM file: %s", path)
        return None


def group_by_series(paths: Iterable[Path]) -> dict[str, list[FileDataset]]:
    """Group readable DICOM datasets by SeriesInstanceUID."""
    groups: dict[str, list[FileDataset]] = defaultdict(list)
    for path in paths:
        ds = _safe_read(path)
        if ds is None:
            continue
        uid = getattr(ds, "SeriesInstanceUID", None)
        if uid is None:
            logger.debug("Dataset without SeriesInstanceUID skipped: %s", path)
            continue
        groups[str(uid)].append(ds)
    return dict(groups)


def _slice_sort_key(ds: FileDataset) -> float:
    """Return a monotonic key ordering slices along the acquisition axis.

    Prefers the projection of ImagePositionPatient onto the slice-normal computed
    from ImageOrientationPatient (robust to oblique acquisitions). Falls back to
    InstanceNumber when geometry is missing.
    """
    ipp = getattr(ds, "ImagePositionPatient", None)
    iop = getattr(ds, "ImageOrientationPatient", None)
    if ipp is not None and iop is not None and len(iop) == 6:
        row = np.array(iop[:3], dtype=float)
        col = np.array(iop[3:], dtype=float)
        normal = np.cross(row, col)
        return float(np.dot(np.array(ipp, dtype=float), normal))
    instance = getattr(ds, "InstanceNumber", 0)
    return float(instance or 0)


class DicomSeries:
    """An ordered DICOM series with a lazily assembled voxel volume."""

    def __init__(self, datasets: list[FileDataset], source_path: str | None = None) -> None:
        if not datasets:
            raise EmptySeriesError("Cannot build a DicomSeries from zero datasets.")
        self.datasets: list[FileDataset] = sorted(datasets, key=_slice_sort_key)
        self.source_path = source_path
        self._volume: np.ndarray | None = None

    @property
    def representative(self) -> FileDataset:
        """The first dataset, used to read series-level attributes."""
        return self.datasets[0]

    def _pixel_spacing(self) -> tuple[float, float] | None:
        ps = getattr(self.representative, "PixelSpacing", None)
        if ps is None or len(ps) < 2:
            return None
        return (float(ps[0]), float(ps[1]))

    @property
    def metadata(self) -> SeriesMetadata:
        """Validated, non-identifying descriptive metadata for the series."""
        ds = self.representative
        return SeriesMetadata(
            series_instance_uid=str(ds.SeriesInstanceUID),
            study_instance_uid=str(getattr(ds, "StudyInstanceUID", "")),
            modality=str(getattr(ds, "Modality", "OT")),
            num_instances=len(self.datasets),
            rows=int(getattr(ds, "Rows", 0)) or None,
            columns=int(getattr(ds, "Columns", 0)) or None,
            pixel_spacing_mm=self._pixel_spacing(),
            slice_thickness_mm=(
                float(ds.SliceThickness) if getattr(ds, "SliceThickness", None) else None
            ),
            manufacturer=str(getattr(ds, "Manufacturer", "")) or None,
            source_path=self.source_path,
        )

    def volume(self) -> np.ndarray:
        """Return the series as a 3D array ``(slices, rows, cols)`` in stored units.

        Rescale slope/intercept are applied so CT data is returned in Hounsfield
        units. The result is cached after first assembly.
        """
        if self._volume is not None:
            return self._volume
        slices: list[np.ndarray] = []
        for ds in self.datasets:
            if _PIXEL_TAG not in ds:
                raise IngestionError(
                    f"Dataset {getattr(ds, 'SOPInstanceUID', '?')} has no pixel data."
                )
            arr = ds.pixel_array.astype(np.float32)
            slope = float(getattr(ds, "RescaleSlope", 1) or 1)
            intercept = float(getattr(ds, "RescaleIntercept", 0) or 0)
            slices.append(arr * slope + intercept)
        try:
            self._volume = np.stack(slices, axis=0)
        except ValueError as exc:  # inconsistent in-plane dimensions
            raise IngestionError(
                "Slices have inconsistent dimensions; cannot stack into a volume."
            ) from exc
        return self._volume

    def __len__(self) -> int:
        return len(self.datasets)


def load_series(path: str | Path, *, series_uid: str | None = None) -> DicomSeries:
    """Load a single DICOM series from ``path``.

    If the path contains multiple series, ``series_uid`` selects one; otherwise
    the largest series (most instances) is chosen and a debug note is logged.
    """
    groups = group_by_series(iter_dicom_files(path))
    if not groups:
        raise EmptySeriesError(f"No readable DICOM series found under: {path}")

    if series_uid is not None:
        if series_uid not in groups:
            raise IngestionError(f"Series {series_uid} not found. Available: {sorted(groups)}")
        chosen = series_uid
    elif len(groups) == 1:
        chosen = next(iter(groups))
    else:
        chosen = max(groups, key=lambda uid: len(groups[uid]))
        logger.debug(
            "Multiple series found (%d); selecting largest %s with %d instances.",
            len(groups),
            chosen,
            len(groups[chosen]),
        )
    return DicomSeries(groups[chosen], source_path=str(path))
