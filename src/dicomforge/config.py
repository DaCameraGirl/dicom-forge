"""Runtime configuration for the dicom-forge pipeline.

Configuration is an explicit, validated object rather than scattered keyword
arguments. It can be built in code, loaded from JSON, or assembled by the CLI,
which keeps the pipeline reproducible and auditable.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

from .deidentify import PSEUDONYM_SECRET_ENV, validate_pseudonym_secret
from .models import BurnedInPolicy, DeidentificationLevel, OutputFormat


class PipelineConfig(BaseModel):
    """Top-level configuration for a single pipeline run."""

    # hide_input_in_errors: validation errors must never echo a rejected secret.
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    deidentify: bool = Field(
        default=True,
        description="De-identify before any data leaves the source environment.",
    )
    deidentification_level: DeidentificationLevel = DeidentificationLevel.MODERATE
    pseudonymise_patient_id: bool = Field(
        default=True,
        description="Replace PatientID with a keyed HMAC pseudonym.",
    )
    pseudonym_secret: SecretStr | None = Field(
        default=None,
        exclude=True,
        description="Private per-project key for PatientID pseudonyms. Never serialised. "
        f"When unset, {PSEUDONYM_SECRET_ENV} is used, else a random per-session key.",
    )
    burned_in_policy: BurnedInPolicy = Field(
        default="reject",
        description="'reject' refuses series with known or suspected burned-in annotation "
        "before anything is written; 'allow' processes them with a warning. Pixel data "
        "is never de-identified either way.",
    )
    output_format: OutputFormat = OutputFormat.NRRD
    fail_on_qc_error: bool = Field(
        default=False,
        description="If True, a failing QC gate aborts the run instead of warning.",
    )

    @model_validator(mode="before")
    @classmethod
    def _reject_legacy_salt(cls, data: Any) -> Any:
        if isinstance(data, dict) and "pseudonym_salt" in data:
            raise ValueError(
                "'pseudonym_salt' was removed: its public default made pseudonyms "
                f"reversible. Set the {PSEUDONYM_SECRET_ENV} environment variable instead "
                "of storing a secret in a config file."
            )
        return data

    @field_validator("pseudonym_secret")
    @classmethod
    def _check_secret(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None:
            validate_pseudonym_secret(value.get_secret_value())
        return value

    @classmethod
    def from_json(cls, path: str | Path) -> PipelineConfig:
        """Load and validate a configuration file."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(data)

    def to_json(self, path: str | Path) -> None:
        """Persist the configuration as indented JSON."""
        Path(path).write_text(self.model_dump_json(indent=2), encoding="utf-8")
