"""Machine-readable output goes to stdout; logs and errors go to stderr.

Before this, Rich log lines were written to stdout ahead of the JSON audit record,
so `dicomforge convert ... > record.json` produced invalid JSON.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dicomforge.cli import app

ENV = {"DICOMFORGE_PSEUDONYM_SECRET": "cli-stream-test-secret-0123456789"}
runner = CliRunner()


@pytest.mark.requires_convert
def test_convert_stdout_is_pure_json(synthetic_series: Path, tmp_path: Path) -> None:
    pytest.importorskip("SimpleITK")
    result = runner.invoke(app, ["convert", str(synthetic_series), str(tmp_path / "vol")], env=ENV)
    assert result.exit_code == 0, result.output
    record = json.loads(result.stdout)  # the whole of stdout parses
    assert record["pixel_privacy"]["status"] == "unverified"
    assert "Loading series" in result.stderr
    assert "Loading series" not in result.stdout


def test_inspect_json_stdout_is_pure_json(synthetic_series: Path) -> None:
    result = runner.invoke(app, ["-v", "inspect", str(synthetic_series), "--json"])
    assert result.exit_code == 0, result.output
    assert len(json.loads(result.stdout)) == 1


def test_qc_json_stdout_is_pure_json(synthetic_series: Path) -> None:
    result = runner.invoke(app, ["qc", str(synthetic_series), "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["num_slices"] == 6
    assert "QC: PASS" in result.stderr  # the log line, not the report


@pytest.mark.requires_convert
def test_missing_secret_warning_goes_to_stderr(
    synthetic_series: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("SimpleITK")
    from dicomforge import deidentify

    monkeypatch.setattr(deidentify, "_process_secret", None)
    monkeypatch.delenv("DICOMFORGE_PSEUDONYM_SECRET", raising=False)
    result = runner.invoke(app, ["convert", str(synthetic_series), str(tmp_path / "vol")])
    assert result.exit_code == 0, result.output
    assert "DICOMFORGE_PSEUDONYM_SECRET" in result.stderr
    json.loads(result.stdout)


@pytest.mark.requires_convert
def test_rejection_message_goes_to_stderr(tmp_path: Path) -> None:
    pytest.importorskip("SimpleITK")
    from test_burned_in import write_series  # fictional series with burned-in text

    src = write_series(tmp_path / "src", burned_in="YES")
    result = runner.invoke(app, ["convert", str(src), str(tmp_path / "vol")], env=ENV)
    assert result.exit_code == 3
    assert "burned-in" in result.stderr.lower()
    assert result.stdout == ""
