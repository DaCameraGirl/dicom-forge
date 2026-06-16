"""End-to-end pipeline tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from dicomforge.config import PipelineConfig
from dicomforge.exceptions import QualityControlError
from dicomforge.ingest import load_series
from dicomforge.models import DeidentificationLevel, OutputFormat
from dicomforge.pipeline import run_pipeline

pytest.importorskip("SimpleITK")


def test_pipeline_end_to_end(synthetic_series: Path, tmp_path: Path) -> None:
    cfg = PipelineConfig(output_format=OutputFormat.NRRD)
    result = run_pipeline(synthetic_series, tmp_path / "out", config=cfg)
    assert result.qc.passed
    assert result.conversion is not None
    assert Path(result.conversion.output_path).exists()
    assert result.deidentification is not None
    assert "PatientName" in result.deidentification.removed_tags


def test_pipeline_deidentifies_in_place(synthetic_series: Path, tmp_path: Path) -> None:
    run_pipeline(
        synthetic_series,
        tmp_path / "out",
        config=PipelineConfig(deidentification_level=DeidentificationLevel.MODERATE),
    )
    # Re-load original files from disk: pipeline de-identifies in memory only,
    # so the source files must be untouched (non-destructive contract).
    reloaded = load_series(synthetic_series)
    assert reloaded.datasets[0].PatientName == "DOE^JANE"


def test_pipeline_no_deid(synthetic_series: Path, tmp_path: Path) -> None:
    result = run_pipeline(
        synthetic_series,
        tmp_path / "out",
        config=PipelineConfig(deidentify=False),
    )
    assert result.deidentification is None


def test_pipeline_fail_on_qc(synthetic_series: Path, tmp_path: Path, monkeypatch) -> None:
    from dicomforge import pipeline as pl

    # Force a failing QC report to verify the gate aborts the run.
    real_load = pl.load_series

    def corrupt_load(*args, **kwargs):
        series = real_load(*args, **kwargs)
        series.datasets[0].Rows = 32
        return series

    monkeypatch.setattr(pl, "load_series", corrupt_load)
    with pytest.raises(QualityControlError):
        run_pipeline(
            synthetic_series, tmp_path / "out", config=PipelineConfig(fail_on_qc_error=True)
        )


def test_pipeline_result_serialises(synthetic_series: Path, tmp_path: Path) -> None:
    result = run_pipeline(synthetic_series, tmp_path / "out")
    payload = result.model_dump_json(indent=2)
    assert "metadata" in payload and "qc" in payload
