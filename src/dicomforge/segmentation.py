"""Segmentation label-map helpers targeting 3D Slicer's ``.seg.nrrd`` format.

A Slicer segmentation is an NRRD scalar volume plus custom header key/value pairs
(``Segment0_Name``, ``Segment0_LabelValue``, ``Segment0_Color`` ...) that tell
Slicer how to render each integer label as a named, coloured segment. We write the
voxels with SimpleITK (for correct geometry) and then inject the Slicer-specific
header fields with pynrrd, which is the combination that produces a file Slicer
loads directly into its Segment Editor.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .convert import _geometry, resolve_output_path
from .exceptions import ConversionError, MissingDependencyError
from .ingest import DicomSeries
from .models import ConversionResult, OutputFormat
from .observability import get_logger

logger = get_logger(__name__)

# A small default palette (RGB 0-1) cycled across segments lacking explicit colours.
_DEFAULT_PALETTE: tuple[tuple[float, float, float], ...] = (
    (0.90, 0.27, 0.27),
    (0.27, 0.62, 0.90),
    (0.40, 0.80, 0.40),
    (0.96, 0.76, 0.26),
    (0.66, 0.40, 0.85),
)


def _require_pynrrd() -> Any:
    """Import pynrrd or raise an actionable MissingDependencyError.

    Returns the ``nrrd`` module (typed ``Any`` as pynrrd ships no stubs).
    """
    try:
        import nrrd
    except ImportError as exc:  # pragma: no cover
        raise MissingDependencyError("pynrrd", "convert") from exc
    return nrrd


def write_labelmap(
    labelmap: np.ndarray,
    reference: DicomSeries,
    output: str | Path,
    *,
    segment_names: dict[int, str] | None = None,
) -> ConversionResult:
    """Write an integer ``labelmap`` as a Slicer ``.seg.nrrd`` segmentation.

    Parameters
    ----------
    labelmap:
        Integer array shaped like ``reference.volume()`` -- ``(slices, rows, cols)``.
        Voxel value ``0`` is background; each positive value is a segment.
    reference:
        The series the labelmap was derived from, used for output geometry.
    segment_names:
        Optional mapping of label value -> human-readable segment name.
    """
    nrrd = _require_pynrrd()

    if labelmap.shape != reference.volume().shape:
        raise ConversionError(
            f"Labelmap shape {labelmap.shape} does not match reference volume "
            f"{reference.volume().shape}."
        )
    labelmap = np.ascontiguousarray(labelmap.astype(np.uint8))

    spacing, origin, direction = _geometry(reference)
    # pynrrd stores data in array order (z, y, x); space directions are row vectors
    # per axis. Build a diagonal-ish matrix from spacing for a faithful round-trip.
    dir_matrix = np.array(direction, float).reshape(3, 3)
    # Columns of dir_matrix are x,y,z axes; scale each by spacing for space directions.
    space_directions = (dir_matrix * np.array(spacing)).T.tolist()

    labels = sorted(int(v) for v in np.unique(labelmap) if v != 0)
    names = segment_names or {}

    header: dict[str, object] = {
        "type": "unsigned char",
        "dimension": 3,
        "space": "left-posterior-superior",
        "space directions": space_directions,
        "space origin": list(origin),
        "kinds": ["domain", "domain", "domain"],
        # Slicer segmentation markers:
        "Segmentation_ContainedRepresentationNames": "Binary labelmap|",
        "Segmentation_MasterRepresentation": "Binary labelmap",
    }
    for idx, label in enumerate(labels):
        colour = _DEFAULT_PALETTE[idx % len(_DEFAULT_PALETTE)]
        prefix = f"Segment{idx}_"
        header[prefix + "ID"] = f"Segment_{label}"
        header[prefix + "Name"] = names.get(label, f"Segment {label}")
        header[prefix + "LabelValue"] = str(label)
        header[prefix + "Layer"] = "0"
        header[prefix + "Color"] = " ".join(f"{c:.3f}" for c in colour)
        header[prefix + "Extent"] = " ".join(str(v) for v in _extent(labelmap, label))

    out_path = resolve_output_path(output, OutputFormat.SEG_NRRD)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # pynrrd expects index order matching header dimension; transpose z,y,x -> x,y,z.
    nrrd.write(str(out_path), labelmap.transpose(2, 1, 0), header)

    logger.info("Wrote segmentation with %d segment(s) -> %s", len(labels), out_path)
    return ConversionResult(
        output_path=str(out_path),
        output_format=OutputFormat.SEG_NRRD,
        shape=tuple(int(s) for s in labelmap.shape[::-1]),
        spacing_mm=tuple(float(s) for s in spacing),
    )


def _extent(labelmap: np.ndarray, label: int) -> tuple[int, int, int, int, int, int]:
    """Return the (zmin,zmax,ymin,ymax,xmin,xmax) bounding box of a label."""
    coords = np.argwhere(labelmap == label)
    if coords.size == 0:
        return (0, -1, 0, -1, 0, -1)
    mins = coords.min(axis=0)
    maxs = coords.max(axis=0)
    return (
        int(mins[0]),
        int(maxs[0]),
        int(mins[1]),
        int(maxs[1]),
        int(mins[2]),
        int(maxs[2]),
    )
