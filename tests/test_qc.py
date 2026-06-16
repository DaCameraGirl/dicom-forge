"""Tests for the quality-control gate."""

from __future__ import annotations

from pathlib import Path

from dicomforge.ingest import load_series
from dicomforge.qc import run_qc


def test_qc_passes_clean_series(synthetic_series: Path) -> None:
    report = run_qc(load_series(synthetic_series))
    assert report.passed
    assert report.geometry_consistent
    assert report.spacing_consistent
    assert report.num_slices == 6


def test_qc_intensity_stats_present(synthetic_series: Path) -> None:
    report = run_qc(load_series(synthetic_series))
    assert report.intensity is not None
    assert report.intensity.minimum <= report.intensity.mean <= report.intensity.maximum
    assert report.intensity.std >= 0


def test_qc_flags_irregular_spacing(synthetic_series: Path) -> None:
    series = load_series(synthetic_series)
    # Corrupt one slice's position to create an irregular gap.
    series.datasets[-1].ImagePositionPatient = [0.0, 0.0, 100.0]
    report = run_qc(series)
    assert not report.spacing_consistent
    assert any("spacing" in w.lower() for w in report.warnings)


def test_qc_flags_inconsistent_geometry(two_series: Path, synthetic_series: Path) -> None:
    series = load_series(synthetic_series)
    series.datasets[0].Rows = 32  # mismatch with the rest
    report = run_qc(series)
    assert not report.geometry_consistent
    assert not report.passed  # geometry mismatch is a hard error


def test_qc_report_serialises(synthetic_series: Path) -> None:
    report = run_qc(load_series(synthetic_series))
    payload = report.model_dump_json()
    assert "series_instance_uid" in payload
