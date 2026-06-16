"""End-to-end orchestration: ingest -> de-identify -> QC -> convert.

The pipeline is the high-level entry point used by both the CLI and the 3D Slicer
extension. It is deterministic given a :class:`~dicomforge.config.PipelineConfig`
and returns a single serialisable :class:`PipelineResult` suitable for an audit log.
The ordering is deliberate: **de-identification happens before conversion**, so any
artefact written to disk is already free of direct identifiers.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from .config import PipelineConfig
from .convert import convert_series
from .deidentify import deidentify_dataset
from .exceptions import QualityControlError
from .ingest import load_series
from .models import (
    ConversionResult,
    DeidentificationResult,
    QCReport,
    SeriesMetadata,
)
from .observability import get_logger
from .qc import run_qc

logger = get_logger(__name__)


class PipelineResult(BaseModel):
    """Complete, serialisable record of one pipeline run."""

    model_config = ConfigDict(extra="forbid")

    metadata: SeriesMetadata
    qc: QCReport
    deidentification: DeidentificationResult | None = None
    conversion: ConversionResult | None = None


def run_pipeline(
    source: str | Path,
    output: str | Path,
    *,
    config: PipelineConfig | None = None,
    series_uid: str | None = None,
) -> PipelineResult:
    """Run the full pipeline on a single series and return its audit record."""
    cfg = config or PipelineConfig()
    logger.info("Loading series from %s", source)
    series = load_series(source, series_uid=series_uid)
    metadata = series.metadata

    deid_result: DeidentificationResult | None = None
    if cfg.deidentify:
        for ds in series.datasets:
            deid_result = deidentify_dataset(
                ds,
                level=cfg.deidentification_level,
                pseudonymise_patient_id=cfg.pseudonymise_patient_id,
                salt=cfg.pseudonym_salt,
            )
        logger.info(
            "De-identified %d instance(s) at level %s",
            len(series),
            cfg.deidentification_level.value,
        )

    qc = run_qc(series)
    if cfg.fail_on_qc_error and not qc.passed:
        raise QualityControlError(
            f"QC failed for series {qc.series_instance_uid}: {'; '.join(qc.errors)}"
        )

    conversion = convert_series(series, output, output_format=cfg.output_format)

    result = PipelineResult(
        metadata=metadata,
        qc=qc,
        deidentification=deid_result,
        conversion=conversion,
    )
    logger.info("Pipeline complete for series %s", metadata.series_instance_uid)
    return result
