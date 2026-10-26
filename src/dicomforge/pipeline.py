"""End-to-end orchestration: ingest -> de-identify -> QC -> convert.

The pipeline is the high-level entry point used by both the CLI and the 3D Slicer
extension. It is deterministic given a :class:`~dicomforge.config.PipelineConfig`
and returns a single serialisable :class:`PipelineResult` suitable for an audit log.
The ordering is deliberate: series flagged for burned-in pixel annotation are
rejected first (see :mod:`dicomforge.pixel_privacy`), and **header de-identification
happens before conversion**. Pixel data itself is never de-identified.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from ._version import __version__
from .config import PipelineConfig
from .convert import convert_series
from .deidentify import combine_results, deidentify_dataset, resolve_pseudonym_secret
from .exceptions import BurnedInAnnotationError, QualityControlError
from .ingest import load_series
from .models import (
    ConversionResult,
    DeidentificationResult,
    PixelPrivacyReport,
    QCReport,
    SeriesMetadata,
)
from .observability import get_logger
from .pixel_privacy import assess_burned_in_risk, rejection_message
from .qc import run_qc

logger = get_logger(__name__)


class PipelineResult(BaseModel):
    """Complete, serialisable record of one pipeline run."""

    model_config = ConfigDict(extra="forbid")

    metadata: SeriesMetadata
    qc: QCReport
    pixel_privacy: PixelPrivacyReport
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
    # Paths and UIDs are never logged: folder names often carry patient identity.
    logger.info("Loading series")
    series = load_series(source, series_uid=series_uid)

    # Pixel data is never de-identified: refuse series known or suspected to carry
    # burned-in annotation before anything is processed or written.
    pixel_privacy = assess_burned_in_risk(series.datasets, policy=cfg.burned_in_policy)
    if pixel_privacy.status == "flagged":
        reasons = ", ".join(pixel_privacy.reasons)
        if cfg.burned_in_policy == "reject":
            logger.warning("Series rejected for burned-in annotation risk (%s)", reasons)
            raise BurnedInAnnotationError(rejection_message(pixel_privacy), pixel_privacy)
        logger.warning(
            "Processing a series flagged for burned-in annotation risk (%s) because "
            "burned_in_policy='allow'. Pixel data is NOT de-identified.",
            reasons,
        )

    deid_result: DeidentificationResult | None = None
    secret: str | None = None
    if cfg.deidentify:
        # Resolve once per run so an invalid secret fails before any work is done.
        secret = resolve_pseudonym_secret(
            cfg.pseudonym_secret.get_secret_value() if cfg.pseudonym_secret is not None else None
        )
        # One audit record for the whole series, not just the last slice (V24).
        deid_result = combine_results(
            [
                deidentify_dataset(
                    ds,
                    level=cfg.deidentification_level,
                    pseudonymise_patient_id=cfg.pseudonymise_patient_id,
                    salt=secret,
                )
                for ds in series.datasets
            ]
        )
        logger.info(
            "De-identified %d instance(s) at level %s",
            len(series),
            cfg.deidentification_level.value,
        )

    # Read audit metadata *after* de-identification so the record carries nothing the
    # de-identified datasets no longer do (their UIDs are already replaced).
    metadata = series.metadata.model_copy(update={"source_path": None})
    qc = run_qc(series)
    if cfg.fail_on_qc_error and not qc.passed:
        raise QualityControlError(
            f"QC failed for series {qc.series_instance_uid}: {'; '.join(qc.errors)}"
        )

    conversion = convert_series(
        series, output, output_format=cfg.output_format, metadata=_provenance(cfg, pixel_privacy)
    )

    result = PipelineResult(
        metadata=metadata,
        qc=qc,
        pixel_privacy=pixel_privacy,
        deidentification=deid_result,
        conversion=conversion,
    )
    logger.info("Pipeline complete (%d slice(s), QC %s)", qc.num_slices, _qc_word(qc))
    return result


def _qc_word(qc: QCReport) -> str:
    return "PASS" if qc.passed else "FAIL"


def _provenance(cfg: PipelineConfig, pixel_privacy: PixelPrivacyReport) -> dict[str, str]:
    """Header fields that keep a converted volume from passing as verified-clean.

    The volume carries no DICOM header, so "header de-identification" records what
    was done to the source headers. Pixel data is never verified: it is either
    "unverified", or "flagged-burned-in-risk-allowed" when the series was flagged
    and processed only because ``burned_in_policy='allow'``.
    """
    return {
        "dicomforge_version": __version__,
        "dicomforge_header_deidentification": (
            cfg.deidentification_level.value if cfg.deidentify else "none"
        ),
        "dicomforge_pixel_data": (
            "flagged-burned-in-risk-allowed" if pixel_privacy.status == "flagged" else "unverified"
        ),
    }
