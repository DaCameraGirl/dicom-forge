"""Runtime configuration for the dicom-forge pipeline.

Configuration is an explicit, validated object rather than scattered keyword
arguments. It can be built in code, loaded from JSON, or assembled by the CLI,
which keeps the pipeline reproducible and auditable.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .models import DeidentificationLevel, OutputFormat


class PipelineConfig(BaseModel):
    """Top-level configuration for a single pipeline run."""

    model_config = ConfigDict(extra="forbid")

    deidentify: bool = Field(
        default=True,
        description="De-identify before any data leaves the source environment.",
    )
    deidentification_level: DeidentificationLevel = DeidentificationLevel.MODERATE
    pseudonymise_patient_id: bool = Field(
        default=True,
        description="Replace PatientID with a deterministic salted hash.",
    )
    pseudonym_salt: str = Field(
        default="dicom-forge",
        description="Salt mixed into the PatientID hash. Override per project so "
        "pseudonyms cannot be correlated across unrelated datasets.",
    )
    output_format: OutputFormat = OutputFormat.NRRD
    fail_on_qc_error: bool = Field(
        default=False,
        description="If True, a failing QC gate aborts the run instead of warning.",
    )

    @classmethod
    def from_json(cls, path: str | Path) -> PipelineConfig:
        """Load and validate a configuration file."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(data)

    def to_json(self, path: str | Path) -> None:
        """Persist the configuration as indented JSON."""
        Path(path).write_text(self.model_dump_json(indent=2), encoding="utf-8")
