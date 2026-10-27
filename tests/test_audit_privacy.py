"""Regression tests: audit records and logs must not carry identifying data.

Audit 2026-10-26 (findings V19, V20): the PipelineResult audit record contained the
original Study/Series Instance UIDs, the input folder path (identifying when a folder
is named after the patient), and metadata captured *before* de-identification (e.g.
Manufacturer survived STRICT). INFO/DEBUG logs contained the input path and UIDs.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
from collections.abc import Iterator
from pathlib import Path

import pydicom
import pytest

from dicomforge.config import PipelineConfig
from dicomforge.exceptions import QualityControlError
from dicomforge.models import DeidentificationLevel
from dicomforge.pipeline import PipelineResult, run_pipeline

pytestmark = pytest.mark.requires_convert  # every test here runs the full pipeline

ENV = "DICOMFORGE_PSEUDONYM_SECRET"
SECRET = "audit-test-secret-0123456789abcdef"
IDENTIFYING_DIR = "DOE_JANE_MRN-0001"
# Identifying values written by tests/conftest.py::_make_slice.
FIXTURE_PHI = ("DOE^JANE", "MRN-0001", "19700101", "123 Test St", "SMITH^JOHN", "General Hospital")
UID_2_25 = re.compile(r"^2\.25\.(0|[1-9][0-9]*)$")
LEVELS = list(DeidentificationLevel)


class _Capture(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.DEBUG)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())

    @property
    def text(self) -> str:
        return "\n".join(self.messages)


@pytest.fixture
def logs() -> Iterator[_Capture]:
    logger = logging.getLogger("dicomforge")
    handler = _Capture()
    old_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    yield handler
    logger.removeHandler(handler)
    logger.setLevel(old_level)


@pytest.fixture(autouse=True)
def _project_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV, SECRET)


@pytest.fixture
def named_study(two_series: Path, tmp_path: Path) -> Path:
    """Two series plus a non-DICOM file, in a folder named after the (fictional) patient."""
    root = tmp_path / "inbox" / IDENTIFYING_DIR
    shutil.copytree(two_series, root)
    (root / "notes.txt").write_text("not dicom", encoding="utf-8")
    return root


def original_uids(root: Path) -> set[str]:
    uids: set[str] = set()
    for path in root.glob("*.dcm"):
        ds = pydicom.dcmread(path)
        uids |= {str(ds.StudyInstanceUID), str(ds.SeriesInstanceUID), str(ds.SOPInstanceUID)}
    return uids


def leaks(text: str, root: Path) -> list[str]:
    needles = [IDENTIFYING_DIR, str(root), *FIXTURE_PHI, *original_uids(root)]
    return [n for n in needles if n in text]


def run(root: Path, out: Path, level: DeidentificationLevel, **cfg: object) -> PipelineResult:
    return run_pipeline(
        root, out / "vol", config=PipelineConfig(deidentification_level=level, **cfg)
    )


# -- audit record --------------------------------------------------------------


@pytest.mark.parametrize("level", LEVELS)
def test_audit_record_has_no_path_uids_or_phi(
    named_study: Path, tmp_path: Path, level: DeidentificationLevel
) -> None:
    result = run(named_study, tmp_path / "out", level)
    assert result.metadata.source_path is None
    assert leaks(result.model_dump_json(), named_study) == []


@pytest.mark.parametrize("level", LEVELS)
def test_audit_uids_are_valid_pseudonymous_uids(
    named_study: Path, tmp_path: Path, level: DeidentificationLevel
) -> None:
    result = run(named_study, tmp_path / "out", level)
    for uid in (result.metadata.series_instance_uid, result.metadata.study_instance_uid):
        assert UID_2_25.match(uid), uid
        assert len(uid) <= 64
    assert result.qc.series_instance_uid == result.metadata.series_instance_uid
    assert result.metadata.series_instance_uid != result.metadata.study_instance_uid


def test_audit_uids_stable_under_same_secret(
    named_study: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    level = DeidentificationLevel.MODERATE
    a = run(named_study, tmp_path / "a", level).metadata
    b = run(named_study, tmp_path / "b", level).metadata
    assert (a.study_instance_uid, a.series_instance_uid) == (
        b.study_instance_uid,
        b.series_instance_uid,
    )
    monkeypatch.setenv(ENV, "a-different-project-secret-000")
    c = run(named_study, tmp_path / "c", level).metadata
    assert c.series_instance_uid != a.series_instance_uid


def test_strict_audit_metadata_reflects_deidentified_data(
    named_study: Path, tmp_path: Path
) -> None:
    # The fixture sets Manufacturer="ForgeSim"; STRICT blanks it in the dataset, so the
    # audit record must not resurrect it from metadata captured before de-identification.
    result = run(named_study, tmp_path / "out", DeidentificationLevel.STRICT)
    assert result.metadata.manufacturer is None
    assert "ForgeSim" not in result.model_dump_json()


def test_no_deid_audit_still_has_no_source_path(named_study: Path, tmp_path: Path) -> None:
    result = run(named_study, tmp_path / "out", DeidentificationLevel.BASIC, deidentify=False)
    assert result.metadata.source_path is None
    assert IDENTIFYING_DIR not in result.model_dump_json()


# -- logs ----------------------------------------------------------------------


@pytest.mark.parametrize("level", LEVELS)
def test_logs_have_no_path_uids_or_phi(
    named_study: Path, tmp_path: Path, logs: _Capture, level: DeidentificationLevel
) -> None:
    out = tmp_path / "out"
    run(named_study, out, level)
    assert logs.messages, "expected the pipeline to log something"
    assert leaks(logs.text, named_study) == []
    assert str(out) not in logs.text


def test_no_deid_logs_have_no_path_or_uids(
    named_study: Path, tmp_path: Path, logs: _Capture
) -> None:
    run(named_study, tmp_path / "out", DeidentificationLevel.BASIC, deidentify=False)
    assert IDENTIFYING_DIR not in logs.text
    assert not any(uid in logs.text for uid in original_uids(named_study))


# -- errors and CLI --------------------------------------------------------------


def test_qc_failure_error_has_no_original_uid(
    named_study: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dicomforge import pipeline as pl

    real_load = pl.load_series

    def corrupt_load(*args, **kwargs):
        series = real_load(*args, **kwargs)
        series.datasets[0].Rows = 32  # inconsistent geometry -> hard QC error
        return series

    monkeypatch.setattr(pl, "load_series", corrupt_load)
    with pytest.raises(QualityControlError) as excinfo:
        run(named_study, tmp_path / "out", DeidentificationLevel.MODERATE, fail_on_qc_error=True)
    assert leaks(str(excinfo.value), named_study) == []


def test_missing_pixel_data_error_has_no_sop_uid(
    named_study: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """QC copies volume-assembly errors into qc.errors, so they must not carry UIDs."""
    from dicomforge import pipeline as pl

    real_load = pl.load_series

    def strip_pixels(*args, **kwargs):
        series = real_load(*args, **kwargs)
        del series.datasets[2].PixelData
        return series

    monkeypatch.setattr(pl, "load_series", strip_pixels)
    with pytest.raises(QualityControlError) as excinfo:
        run(named_study, tmp_path / "out", DeidentificationLevel.MODERATE, fail_on_qc_error=True)
    assert "pixel data" in str(excinfo.value)
    assert leaks(str(excinfo.value), named_study) == []


def test_cli_convert_output_has_no_path_or_uids(named_study: Path, tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from dicomforge.cli import app

    result = CliRunner().invoke(
        app, ["convert", str(named_study), str(tmp_path / "out" / "vol")], env={ENV: SECRET}
    )
    assert result.exit_code == 0, result.output
    assert leaks(result.output, named_study) == []


# -- contract kept for the Slicer extension ------------------------------------


def test_slicer_extension_contract_preserved(named_study: Path, tmp_path: Path) -> None:
    """Fields DicomForgeBatch.py reads (lines 183-185, 374-383) are still present."""
    record = run(named_study, tmp_path / "out", DeidentificationLevel.MODERATE).model_dump(
        mode="json"
    )
    assert record["metadata"]["modality"] == "CT"
    assert record["qc"]["num_slices"] == 6
    assert record["qc"]["errors"] == [] and isinstance(record["qc"]["warnings"], list)
    assert Path(record["conversion"]["output_path"]).exists()
    json.dumps(record)  # serialisable, as the extension stores it
