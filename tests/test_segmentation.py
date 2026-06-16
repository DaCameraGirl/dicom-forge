"""Tests for Slicer .seg.nrrd segmentation writing."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from dicomforge.exceptions import ConversionError
from dicomforge.ingest import load_series
from dicomforge.segmentation import write_labelmap

pytest.importorskip("nrrd")
pytestmark = pytest.mark.requires_convert


def _labelmap_like(series) -> np.ndarray:
    vol = series.volume()
    lm = np.zeros(vol.shape, dtype=np.uint8)
    lm[:, 4:8, 4:8] = 1  # segment 1
    lm[:, 10:12, 10:12] = 2  # segment 2
    return lm


def test_write_labelmap_creates_file(synthetic_series: Path, tmp_path: Path) -> None:
    series = load_series(synthetic_series)
    result = write_labelmap(
        _labelmap_like(series),
        series,
        tmp_path / "seg",
        segment_names={1: "Liver", 2: "Tumor"},
    )
    out = Path(result.output_path)
    assert out.exists()
    assert out.name.endswith(".seg.nrrd")


def test_segmentation_header_has_slicer_fields(synthetic_series: Path, tmp_path: Path) -> None:
    import nrrd

    series = load_series(synthetic_series)
    result = write_labelmap(
        _labelmap_like(series),
        series,
        tmp_path / "seg",
        segment_names={1: "Liver", 2: "Tumor"},
    )
    _, header = nrrd.read(result.output_path)
    assert header["Segment0_Name"] == "Liver"
    assert header["Segment1_Name"] == "Tumor"
    assert header["Segmentation_MasterRepresentation"] == "Binary labelmap"


def test_labelmap_shape_mismatch_raises(synthetic_series: Path, tmp_path: Path) -> None:
    series = load_series(synthetic_series)
    bad = np.zeros((2, 2, 2), dtype=np.uint8)
    with pytest.raises(ConversionError):
        write_labelmap(bad, series, tmp_path / "seg")
