"""Tests for the Typer CLI via Typer's test runner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dicomforge import __version__
from dicomforge.cli import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_inspect_table(synthetic_series: Path) -> None:
    result = runner.invoke(app, ["inspect", str(synthetic_series)])
    assert result.exit_code == 0
    assert "CT" in result.stdout


def test_inspect_json(synthetic_series: Path) -> None:
    result = runner.invoke(app, ["inspect", str(synthetic_series), "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert len(payload) == 1


def test_qc_command(synthetic_series: Path) -> None:
    result = runner.invoke(app, ["qc", str(synthetic_series)])
    assert result.exit_code == 0
    assert "PASS" in result.stdout


@pytest.mark.requires_convert
def test_convert_command(synthetic_series: Path, tmp_path: Path) -> None:
    pytest.importorskip("SimpleITK")
    out = tmp_path / "vol"
    result = runner.invoke(app, ["convert", str(synthetic_series), str(out), "--format", "nrrd"])
    assert result.exit_code == 0
    assert (tmp_path / "vol.nrrd").exists()


def test_inspect_empty_dir(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    result = runner.invoke(app, ["inspect", str(empty)])
    assert result.exit_code == 1
