"""Tests for DICOM discovery, grouping, sorting, and volume assembly."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from dicomforge.exceptions import EmptySeriesError, IngestionError
from dicomforge.ingest import (
    DicomSeries,
    group_by_series,
    iter_dicom_files,
    load_series,
)


def test_iter_dicom_files_finds_all(synthetic_series: Path) -> None:
    files = list(iter_dicom_files(synthetic_series))
    assert len(files) == 6
    assert all(f.suffix == ".dcm" for f in files)


def test_iter_dicom_files_missing_path() -> None:
    with pytest.raises(IngestionError):
        list(iter_dicom_files("does/not/exist"))


def test_group_by_series_single(synthetic_series: Path) -> None:
    groups = group_by_series(iter_dicom_files(synthetic_series))
    assert len(groups) == 1
    (datasets,) = groups.values()
    assert len(datasets) == 6


def test_group_by_series_ignores_non_dicom(synthetic_series: Path) -> None:
    (synthetic_series / "notes.txt").write_text("not dicom", encoding="utf-8")
    groups = group_by_series(iter_dicom_files(synthetic_series))
    assert sum(len(v) for v in groups.values()) == 6


def test_load_series_metadata(synthetic_series: Path) -> None:
    series = load_series(synthetic_series)
    meta = series.metadata
    assert meta.modality == "CT"
    assert meta.num_instances == 6
    assert meta.rows == 16 and meta.columns == 16
    assert meta.pixel_spacing_mm == (0.7, 0.7)


def test_volume_shape_and_rescale(synthetic_series: Path) -> None:
    series = load_series(synthetic_series)
    vol = series.volume()
    assert vol.shape == (6, 16, 16)
    # RescaleIntercept is -1024, so HU minimum should be at least that low.
    assert vol.min() <= -1000
    # Caching returns the same array object.
    assert series.volume() is vol


def test_slices_sorted_by_position(synthetic_series: Path) -> None:
    series = load_series(synthetic_series)
    zs = [ds.ImagePositionPatient[2] for ds in series.datasets]
    assert zs == sorted(zs)


def test_load_series_selects_largest(two_series: Path) -> None:
    series = load_series(two_series)
    assert len(series) == 6  # the larger of the two (6 vs 3)


def test_load_series_explicit_uid(two_series: Path) -> None:
    groups = group_by_series(iter_dicom_files(two_series))
    small_uid = min(groups, key=lambda u: len(groups[u]))
    series = load_series(two_series, series_uid=small_uid)
    assert len(series) == 3


def test_load_series_unknown_uid(synthetic_series: Path) -> None:
    with pytest.raises(IngestionError):
        load_series(synthetic_series, series_uid="1.2.3.not.here")


def test_empty_series_raises(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(EmptySeriesError):
        load_series(empty)


def test_dicomseries_requires_datasets() -> None:
    with pytest.raises(EmptySeriesError):
        DicomSeries([])


def test_volume_is_float32(synthetic_series: Path) -> None:
    vol = load_series(synthetic_series).volume()
    assert vol.dtype == np.float32
