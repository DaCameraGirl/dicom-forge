"""Tests for volume conversion to NIfTI/NRRD via SimpleITK.

These require the optional 'convert' extra. They are marked so a core-only CI lane
can deselect them with ``-m 'not requires_convert'``.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from dicomforge.convert import convert_series, resolve_output_path, series_to_image
from dicomforge.exceptions import MissingDependencyError
from dicomforge.ingest import load_series
from dicomforge.models import OutputFormat

pytest.importorskip("SimpleITK")
pytestmark = pytest.mark.requires_convert


def test_resolve_output_path_adds_extension() -> None:
    assert resolve_output_path("out", OutputFormat.NRRD).name == "out.nrrd"
    assert resolve_output_path("out", OutputFormat.NIFTI).name == "out.nii.gz"
    assert resolve_output_path("out.nrrd", OutputFormat.NIFTI).name == "out.nii.gz"


def test_series_to_image_geometry(synthetic_series: Path) -> None:
    series = load_series(synthetic_series)
    image = series_to_image(series)
    # SimpleITK size is (x, y, z); volume is (z, y, x).
    assert image.GetSize() == (16, 16, 6)
    sx, sy, sz = image.GetSpacing()
    assert (round(sx, 3), round(sy, 3)) == (0.7, 0.7)
    assert round(sz, 3) == 1.0


@pytest.mark.parametrize("fmt", [OutputFormat.NRRD, OutputFormat.NIFTI])
def test_convert_writes_file(synthetic_series: Path, tmp_path: Path, fmt) -> None:
    series = load_series(synthetic_series)
    out = tmp_path / "vol"
    result = convert_series(series, out, output_format=fmt)
    assert Path(result.output_path).exists()
    assert result.output_format is fmt
    assert result.shape == (16, 16, 6)


def test_convert_roundtrip_values(synthetic_series: Path, tmp_path: Path) -> None:
    import SimpleITK as sitk

    series = load_series(synthetic_series)
    result = convert_series(series, tmp_path / "vol", output_format=OutputFormat.NRRD)
    reloaded = sitk.GetArrayFromImage(sitk.ReadImage(result.output_path))
    np.testing.assert_allclose(reloaded, series.volume(), rtol=0, atol=1e-3)


def test_missing_dependency_message(monkeypatch) -> None:
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "SimpleITK":
            raise ImportError("simulated absence")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    from dicomforge import convert

    with pytest.raises(MissingDependencyError) as exc:
        convert._require_sitk()
    assert "convert" in str(exc.value)
