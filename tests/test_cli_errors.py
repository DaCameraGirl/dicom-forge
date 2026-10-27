"""CLI failure paths: clean one-line errors on stderr, documented exit codes, no leaks.

Before this, engine errors escaped as Rich tracebacks (exit 1), `--series` with an
unknown UID listed every original Series UID in the input, and ingestion errors
echoed the input path.

Exit codes: 0 success, 1 processing error, 2 QC failure (Typer also uses 2 for usage
errors), 3 burned-in annotation rejection, 4 configuration error.
"""

from __future__ import annotations

from pathlib import Path

import pydicom
import pytest
from pydicom.uid import generate_uid
from typer.testing import CliRunner

from _dicomio import save_dicom
from conftest import _make_slice
from dicomforge.cli import app

ENV = {"DICOMFORGE_PSEUDONYM_SECRET": "cli-error-test-secret-0123456789"}
runner = CliRunner()


def _invoke(args: list[str], env: dict[str, str] | None = None):
    result = runner.invoke(app, args, env=env if env is not None else ENV)
    # A clean failure ends with SystemExit, never an escaped engine exception.
    assert result.exception is None or isinstance(result.exception, SystemExit), repr(
        result.exception
    )
    assert "Traceback" not in result.output
    return result


@pytest.fixture
def bad_geometry(tmp_path: Path) -> Path:
    root = tmp_path / "PATIENT_FOLDER_badgeo"
    root.mkdir()
    study, series = generate_uid(), generate_uid()
    for i in range(4):
        size = 32 if i == 0 else 16  # one slice with different dimensions
        ds = _make_slice(
            study_uid=study, series_uid=series, index=i, z=float(i), rows=size, cols=size
        )
        save_dicom(ds, root / f"{i}.dcm")
    return root


@pytest.fixture
def no_dicom(tmp_path: Path) -> Path:
    root = tmp_path / "PATIENT_FOLDER_empty"
    root.mkdir()
    (root / "notes.txt").write_text("not dicom", encoding="utf-8")
    return root


@pytest.mark.requires_convert
def test_qc_gate_failure_exits_2(bad_geometry: Path, tmp_path: Path) -> None:
    result = _invoke(["convert", str(bad_geometry), str(tmp_path / "v"), "--fail-on-qc"])
    assert result.exit_code == 2
    assert "QC failed" in result.stderr
    assert result.stdout == ""


@pytest.mark.requires_convert
def test_conversion_error_exits_1_cleanly(bad_geometry: Path, tmp_path: Path) -> None:
    result = _invoke(["convert", str(bad_geometry), str(tmp_path / "v")])
    assert result.exit_code == 1
    assert result.stderr.strip().splitlines()[-1].startswith("Error:")  # after INFO logs
    assert result.stdout == ""


@pytest.mark.parametrize("command", ["convert", "qc"])
def test_no_dicom_exits_1_without_echoing_path(
    command: str, no_dicom: Path, tmp_path: Path
) -> None:
    args = [command, str(no_dicom)] + ([str(tmp_path / "v")] if command == "convert" else [])
    result = _invoke(args)
    assert result.exit_code == 1
    assert "No readable DICOM" in result.stderr
    assert "PATIENT_FOLDER" not in result.output
    assert result.stdout == ""


def test_inspect_no_dicom_reports_on_stderr(no_dicom: Path) -> None:
    result = _invoke(["inspect", str(no_dicom), "--json"])
    assert result.exit_code == 1
    assert result.stdout == ""
    assert "No readable DICOM" in result.stderr


@pytest.mark.requires_convert
def test_invalid_secret_exits_4(synthetic_series: Path, tmp_path: Path) -> None:
    result = _invoke(
        ["convert", str(synthetic_series), str(tmp_path / "v")],
        env={"DICOMFORGE_PSEUDONYM_SECRET": "short"},
    )
    assert result.exit_code == 4
    assert "at least 16" in result.stderr
    assert "short" not in result.stderr.replace("at least", "")  # secret not echoed


@pytest.mark.parametrize("command", ["convert", "qc"])
def test_unknown_series_does_not_list_original_uids(
    command: str, synthetic_series: Path, tmp_path: Path
) -> None:
    original = str(pydicom.dcmread(next(synthetic_series.glob("*.dcm"))).SeriesInstanceUID)
    args = [command, str(synthetic_series)]
    if command == "convert":
        args.append(str(tmp_path / "v"))
    result = _invoke([*args, "--series", "1.2.3.4"])
    assert result.exit_code == 1
    assert original not in result.output
    assert "inspect" in result.stderr  # points to the command that lists series


def test_ingest_errors_do_not_echo_paths(tmp_path: Path) -> None:
    from dicomforge.exceptions import IngestionError
    from dicomforge.ingest import iter_dicom_files, load_series

    missing = tmp_path / "PATIENT_FOLDER_missing"
    with pytest.raises(IngestionError) as excinfo:
        list(iter_dicom_files(missing))
    assert "PATIENT_FOLDER" not in str(excinfo.value)
    empty = tmp_path / "PATIENT_FOLDER_none"
    empty.mkdir()
    with pytest.raises(IngestionError) as excinfo:
        load_series(empty)
    assert "PATIENT_FOLDER" not in str(excinfo.value)
