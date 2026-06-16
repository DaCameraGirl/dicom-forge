"""Command-line interface for dicom-forge, built with Typer.

Commands:
  inspect    Summarise the series found under a path (no data is written).
  qc         Run quality control and print/serialise the report.
  convert    Run the full pipeline (de-id -> QC -> convert) on a series.

Every command prints a Rich table for humans and supports ``--json`` for machines,
so the same binary serves interactive use and CI/pipeline automation.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .config import PipelineConfig
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
console = Console()


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
    """List the DICOM series found under PATH."""
    groups = group_by_series(iter_dicom_files(path))
    if not groups:
        console.print("[yellow]No readable DICOM series found.[/yellow]")
        raise typer.Exit(code=1)

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
    """Run quality control on a series and report findings."""
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
        raise typer.Exit(code=2)


@app.command()
def convert(
    path: Path = typer.Argument(..., exists=True, help="DICOM file or directory."),
    output: Path = typer.Argument(..., help="Output volume path (extension auto-added)."),
    fmt: OutputFormat = typer.Option(OutputFormat.NRRD, "--format", "-f", help="Output format."),
    level: DeidentificationLevel = typer.Option(
        DeidentificationLevel.MODERATE, "--deid-level", help="De-identification level."
    ),
    no_deid: bool = typer.Option(False, "--no-deid", help="Skip de-identification (unsafe)."),
    fail_on_qc: bool = typer.Option(False, "--fail-on-qc", help="Abort if QC fails."),
    series_uid: str | None = typer.Option(None, "--series", help="Select a series UID."),
) -> None:
    """Run the full pipeline and write a converted volume."""
    cfg = PipelineConfig(
        deidentify=not no_deid,
        deidentification_level=level,
        output_format=fmt,
        fail_on_qc_error=fail_on_qc,
    )
    result = run_pipeline(path, output, config=cfg, series_uid=series_uid)
    console.print_json(result.model_dump_json(indent=2))


if __name__ == "__main__":  # pragma: no cover
    app()
