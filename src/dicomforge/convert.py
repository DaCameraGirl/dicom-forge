"""Volume conversion to viewer-native formats (NIfTI, NRRD).

SimpleITK (the same ITK core that powers 3D Slicer and ITK-SNAP) is an *optional*
dependency, imported lazily so the rest of dicom-forge runs without it. Geometry
(spacing, origin, orientation) is reconstructed from the DICOM headers and applied
to the output so volumes load into Slicer/ITK-SNAP in correct anatomical space.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .exceptions import ConversionError, MissingDependencyError
from .ingest import DicomSeries
from .models import ConversionResult, OutputFormat
from .observability import get_logger

# SimpleITK is a C++ library exposed via SWIG with no type stubs. We treat its
# objects as ``Any`` at this boundary so the rest of the codebase stays strictly
# typed without scattering per-call ``# type: ignore`` comments.
logger = get_logger(__name__)

_EXTENSIONS: dict[OutputFormat, str] = {
    OutputFormat.NIFTI: ".nii.gz",
    OutputFormat.NRRD: ".nrrd",
    OutputFormat.SEG_NRRD: ".seg.nrrd",
}


def _require_sitk() -> Any:
    """Import SimpleITK or raise an actionable MissingDependencyError."""
    try:
        import SimpleITK as sitk
    except ImportError as exc:  # pragma: no cover - exercised via monkeypatch
        raise MissingDependencyError("SimpleITK", "convert") from exc
    return sitk


def _geometry(
    series: DicomSeries,
) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, ...]]:
    """Reconstruct (spacing_xyz, origin_xyz, direction) from DICOM headers.

    Falls back to identity geometry with unit spacing when headers are absent,
    so conversion still succeeds (with a warning logged by the caller).
    """
    ds = series.representative
    ps = getattr(ds, "PixelSpacing", None)
    row_spacing = float(ps[0]) if ps else 1.0
    col_spacing = float(ps[1]) if ps else 1.0

    # Slice spacing from the first two slice positions when geometry exists.
    slice_spacing = float(getattr(ds, "SliceThickness", 0) or 0) or 1.0
    if len(series) >= 2:
        iop = getattr(ds, "ImageOrientationPatient", None)
        ipp0 = getattr(series.datasets[0], "ImagePositionPatient", None)
        ipp1 = getattr(series.datasets[1], "ImagePositionPatient", None)
        if iop is not None and ipp0 is not None and ipp1 is not None and len(iop) == 6:
            normal = np.cross(np.array(iop[:3], float), np.array(iop[3:], float))
            delta = np.array(ipp1, float) - np.array(ipp0, float)
            measured = abs(float(np.dot(delta, normal)))
            if measured > 0:
                slice_spacing = measured

    # SimpleITK spacing order is (x, y, z) = (col, row, slice).
    spacing = (col_spacing, row_spacing, slice_spacing)

    ipp = getattr(ds, "ImagePositionPatient", None)
    origin = tuple(float(v) for v in ipp) if ipp and len(ipp) == 3 else (0.0, 0.0, 0.0)

    iop = getattr(ds, "ImageOrientationPatient", None)
    if iop is not None and len(iop) == 6:
        row = np.array(iop[:3], float)
        col = np.array(iop[3:], float)
        normal = np.cross(row, col)
        # ITK direction is column-major 3x3 flattened: columns are x,y,z axes.
        direction = tuple(np.column_stack([row, col, normal]).flatten(order="C").tolist())
    else:
        direction = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)

    return spacing, origin, direction  # type: ignore[return-value]


def series_to_image(series: DicomSeries) -> Any:
    """Build a geometry-aware SimpleITK image from an in-memory series.

    Returns a ``SimpleITK.Image`` (typed ``Any`` as SimpleITK ships no stubs).
    """
    sitk = _require_sitk()
    volume = series.volume()  # (slices, rows, cols) == (z, y, x)
    image = sitk.GetImageFromArray(volume)
    spacing, origin, direction = _geometry(series)
    image.SetSpacing(spacing)
    image.SetOrigin(origin)
    image.SetDirection(direction)
    return image


def resolve_output_path(output: str | Path, fmt: OutputFormat) -> Path:
    """Append the canonical extension for ``fmt`` if the path lacks one."""
    path = Path(output)
    ext = _EXTENSIONS[fmt]
    if path.name.endswith(ext):
        return path
    # Strip a bare ".nrrd"/".nii" if the caller gave the wrong one, then append.
    stem = path.name
    for known in (".seg.nrrd", ".nii.gz", ".nrrd", ".nii"):
        if stem.endswith(known):
            stem = stem[: -len(known)]
            break
    return path.with_name(stem + ext)


def convert_series(
    series: DicomSeries,
    output: str | Path,
    *,
    output_format: OutputFormat = OutputFormat.NRRD,
) -> ConversionResult:
    """Convert ``series`` to ``output`` in the requested format.

    Returns a :class:`ConversionResult` recording the written path, shape, and
    spacing. Raises :class:`ConversionError` if SimpleITK fails to write.
    """
    sitk = _require_sitk()
    image = series_to_image(series)
    out_path = resolve_output_path(output, output_format)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        # useCompression keeps .nii.gz / .nrrd small; True is safe for both.
        sitk.WriteImage(image, str(out_path), useCompression=True)
    except RuntimeError as exc:
        raise ConversionError(f"SimpleITK failed to write {out_path}: {exc}") from exc

    result = ConversionResult(
        output_path=str(out_path),
        output_format=output_format,
        shape=tuple(int(s) for s in image.GetSize()),
        spacing_mm=tuple(float(s) for s in image.GetSpacing()),
    )
    logger.info("Wrote %s volume %s -> %s", output_format.value, result.shape, out_path)
    return result
