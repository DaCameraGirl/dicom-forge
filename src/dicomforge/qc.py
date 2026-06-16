"""Quality control for ingested DICOM series.

QC runs *before* conversion so problems (missing slices, irregular spacing,
inconsistent geometry) are caught while the original DICOM is still available to
investigate. Findings are split into ``warnings`` (non-blocking) and ``errors``
(blocking when ``fail_on_qc_error`` is set), and the report is fully serialisable
for inclusion in an audit trail.
"""

from __future__ import annotations

import numpy as np

from .ingest import DicomSeries
from .models import IntensityStats, QCReport
from .observability import get_logger

logger = get_logger(__name__)

# A series with fewer than this many slices is flagged as not a true volume.
_MIN_VOLUME_SLICES = 3
# Relative tolerance for declaring slice spacing "regular".
_SPACING_RTOL = 0.01


def _slice_positions(series: DicomSeries) -> list[float] | None:
    """Z-positions of slices along the acquisition normal, if geometry exists."""
    positions: list[float] = []
    for ds in series.datasets:
        ipp = getattr(ds, "ImagePositionPatient", None)
        iop = getattr(ds, "ImageOrientationPatient", None)
        if ipp is None or iop is None or len(iop) != 6:
            return None
        row = np.array(iop[:3], dtype=float)
        col = np.array(iop[3:], dtype=float)
        normal = np.cross(row, col)
        positions.append(float(np.dot(np.array(ipp, dtype=float), normal)))
    return positions


def _check_spacing(series: DicomSeries, warnings: list[str], errors: list[str]) -> bool:
    """Return True when inter-slice spacing is regular within tolerance."""
    positions = _slice_positions(series)
    if positions is None or len(positions) < 2:
        warnings.append("Slice geometry unavailable; spacing not verified.")
        return False
    diffs = np.diff(np.array(positions))
    if np.any(diffs <= 0):
        warnings.append("Non-monotonic slice positions detected after sorting.")
    median = float(np.median(np.abs(diffs)))
    if median == 0:
        errors.append("Zero median slice spacing; slices may be duplicated.")
        return False
    spread = float(np.max(np.abs(diffs)) - np.min(np.abs(diffs)))
    if spread > _SPACING_RTOL * median:
        warnings.append(
            f"Irregular slice spacing (spread {spread:.4f} mm around {median:.4f} mm); "
            "resampling recommended before quantitative analysis."
        )
        return False
    return True


def _check_geometry(series: DicomSeries, errors: list[str]) -> bool:
    """Return True when all slices share in-plane dimensions."""
    shapes = {
        (int(getattr(ds, "Rows", 0)), int(getattr(ds, "Columns", 0))) for ds in series.datasets
    }
    if len(shapes) > 1:
        errors.append(f"Inconsistent in-plane dimensions across slices: {sorted(shapes)}.")
        return False
    return True


def run_qc(series: DicomSeries) -> QCReport:
    """Run all QC checks against ``series`` and return a structured report."""
    warnings: list[str] = []
    errors: list[str] = []

    num_slices = len(series)
    if num_slices < _MIN_VOLUME_SLICES:
        warnings.append(f"Series has only {num_slices} slice(s); treat as 2D rather than a volume.")

    geometry_ok = _check_geometry(series, errors)
    spacing_ok = _check_spacing(series, warnings, errors)

    intensity: IntensityStats | None = None
    if geometry_ok:
        try:
            vol = series.volume()
            intensity = IntensityStats(
                minimum=float(np.min(vol)),
                maximum=float(np.max(vol)),
                mean=float(np.mean(vol)),
                std=float(np.std(vol)),
            )
        except Exception as exc:
            errors.append(f"Could not assemble volume for intensity QC: {exc}")

    report = QCReport(
        series_instance_uid=series.metadata.series_instance_uid,
        num_slices=num_slices,
        spacing_consistent=spacing_ok,
        geometry_consistent=geometry_ok,
        intensity=intensity,
        warnings=tuple(warnings),
        errors=tuple(errors),
    )
    logger.info(
        "QC %s: %s (warnings=%d errors=%d)",
        report.series_instance_uid,
        "PASS" if report.passed else "FAIL",
        len(report.warnings),
        len(report.errors),
    )
    return report
