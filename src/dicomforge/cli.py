"""Command-line interface for dicom-forge, built with Typer.

Commands:
  inspect    Summarise the series found under a path (no data is written).
  qc         Run quality control and print/serialise the report.
  convert    Run the full pipeline (de-id -> QC -> convert) on a series.

Every command prints a Rich table for humans and supports ``--json`` for machines,
so the same binary serves interactive use and CI/pipeline automation.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import NoReturn

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .config import PipelineConfig
from .exceptions import (
    BurnedInAnnotationError,
    ConfigurationError,
    DicomForgeError,
    QualityControlError,
)
from .ingest import group_by_series, iter_dicom_files, load_series
from .models import DeidentificationLevel, OutputFormat
from .observability import configure_logging
from .pipeline import run_pipeline
from .qc import run_qc

app = typer.Typer(
    name="dicomforge",
    help="Enterprise medical-imaging pipeline for 3D Slicer & ITK-SNAP.",
    no_args_is_help=True,
    add_completion=False,
)
#: Exit codes (Typer itself also exits 2 on a usage error).
EXIT_ERROR = 1  # processing error: unreadable input, conversion failure, ...
EXIT_QC_FAILED = 2  # QC reported a hard error (`qc`, or `convert --fail-on-qc`)
EXIT_BURNED_IN = 3  # series rejected for burned-in annotation risk
EXIT_CONFIG = 4  # invalid configuration, e.g. an unsafe pseudonymisation secret

console = Console()  # stdout: results only (tables, JSON)
err_console = Console(stderr=True)  # stderr: errors and diagnostics


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"dicom-forge {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
    _version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """Configure global options for all commands."""
    configure_logging("DEBUG" if verbose else "INFO")


@app.command()
def inspect(
    path: Path = typer.Argument(..., exists=True, help="DICOM file or directory."),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
) -> None:
    """List the DICOM series found under PATH.

    Reads the original data and prints original UIDs and paths: don't share its output.
    """
    with _cli_errors():
        groups = group_by_series(iter_dicom_files(path))
    if not groups:
        err_console.print("No readable DICOM series found.", style="yellow")
        raise typer.Exit(code=EXIT_ERROR)

    if as_json:
        import json

        payload = {uid: load_series(path, series_uid=uid).metadata.model_dump() for uid in groups}
        console.print_json(json.dumps(payload))
        return

    table = Table(title=f"DICOM series under {path}")
    table.add_column("Series UID", overflow="fold")
    table.add_column("Modality")
    table.add_column("Instances", justify="right")
    table.add_column("Dimensions")
    for uid in groups:
        meta = load_series(path, series_uid=uid).metadata
        dims = f"{meta.rows}x{meta.columns}" if meta.rows else "-"
        table.add_row(uid, meta.modality, str(meta.num_instances), dims)
    console.print(table)


@app.command()
def qc(
    path: Path = typer.Argument(..., exists=True, help="DICOM file or directory."),
    series_uid: str | None = typer.Option(None, "--series", help="Select a series UID."),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
) -> None:
    """Run quality control on a series and report findings.

    Reads the original data (no de-identification), so the report carries the
    original Series UID: don't share its output.
    """
    with _cli_errors():
        series = load_series(path, series_uid=series_uid)
        report = run_qc(series)

    if as_json:
        console.print_json(report.model_dump_json())
    else:
        status = "[green]PASS[/green]" if report.passed else "[red]FAIL[/red]"
        console.print(f"QC {report.series_instance_uid}: {status}")
        console.print(
            f"  slices={report.num_slices} "
            f"spacing_consistent={report.spacing_consistent} "
            f"geometry_consistent={report.geometry_consistent}"
        )
        for w in report.warnings:
            console.print(f"  [yellow]warning[/yellow]: {w}")
        for e in report.errors:
            console.print(f"  [red]error[/red]: {e}")
    if not report.passed:
        raise typer.Exit(code=EXIT_QC_FAILED)


@app.command()
def convert(
    path: Path = typer.Argument(..., exists=True, help="DICOM file or directory."),
    output: Path = typer.Argument(..., help="Output volume path (extension auto-added)."),
    fmt: OutputFormat = typer.Option(OutputFormat.NRRD, "--format", "-f", help="Output format."),
    level: DeidentificationLevel = typer.Option(
        DeidentificationLevel.MODERATE, "--deid-level", help="De-identification level."
    ),
    no_deid: bool = typer.Option(False, "--no-deid", help="Skip de-identification (unsafe)."),
    allow_burned_in: bool = typer.Option(
        False,
        "--allow-burned-in",
        help="Process series flagged for burned-in pixel annotation (unsafe: pixel data "
        "is never de-identified). Use only after reviewing the images.",
    ),
    fail_on_qc: bool = typer.Option(False, "--fail-on-qc", help="Abort if QC fails."),
    series_uid: str | None = typer.Option(None, "--series", help="Select a series UID."),
) -> None:
    """Run the full pipeline and write a converted volume.

    PatientID pseudonyms are keyed by the DICOMFORGE_PSEUDONYM_SECRET environment
    variable; without it a random per-run key is used (pseudonyms not stable).
    """
    cfg = PipelineConfig(
        deidentify=not no_deid,
        deidentification_level=level,
        output_format=fmt,
        fail_on_qc_error=fail_on_qc,
        burned_in_policy="allow" if allow_burned_in else "reject",
    )
    with _cli_errors():
        result = run_pipeline(path, output, config=cfg, series_uid=series_uid)
    console.print_json(result.model_dump_json(indent=2))


@contextmanager
def _cli_errors() -> Iterator[None]:
    """Turn engine errors into one-line stderr messages and documented exit codes.

    No traceback is printed: it would repeat values (and, before 0.2.0, identifiers)
    that the message deliberately leaves out. Unexpected exceptions still propagate.
    """
    try:
        yield
    except BurnedInAnnotationError as exc:
        _fail("Rejected (burned-in annotation risk):", exc, EXIT_BURNED_IN)
    except QualityControlError as exc:
        _fail("Error:", exc, EXIT_QC_FAILED)
    except ConfigurationError as exc:
        _fail("Configuration error:", exc, EXIT_CONFIG)
    except DicomForgeError as exc:
        _fail("Error:", exc, EXIT_ERROR)


def _fail(prefix: str, exc: Exception, code: int) -> NoReturn:
    err_console.print(prefix, str(exc), markup=False, highlight=False)
    raise typer.Exit(code=code) from exc


if __name__ == "__main__":  # pragma: no cover
    app()
