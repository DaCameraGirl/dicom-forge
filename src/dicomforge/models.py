"""Pydantic data models that form the public contract of dicom-forge.

Every stage of the pipeline (ingest -> de-identify -> QC -> convert) produces an
immutable, validated record. Using Pydantic gives us free validation, JSON
serialisation for audit trails, and self-documenting schemas that the CLI and the
3D Slicer extension can both rely on.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

#: What to do with a series flagged for burned-in annotation risk.
BurnedInPolicy = Literal["reject", "allow"]


class _Frozen(BaseModel):
    """Base for immutable value objects with strict validation."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class OutputFormat(str, Enum):
    """Volume output formats understood by downstream viewers."""

    NIFTI = "nifti"  # .nii.gz -- ITK-SNAP / neuroimaging standard
    NRRD = "nrrd"  # .nrrd  -- 3D Slicer native scalar volume
    SEG_NRRD = "seg-nrrd"  # .seg.nrrd -- 3D Slicer native segmentation


class DeidentificationLevel(str, Enum):
    """How aggressively patient-identifying data is removed.

    Loosely tracks the DICOM PS3.15 Basic Application Level Confidentiality
    Profile and its retention options.
    """

    BASIC = "basic"  # remove direct identifiers, keep dates and structure
    MODERATE = "moderate"  # also shift/blank dates and device identifiers
    STRICT = "strict"  # blank everything not on a clinical safe-list


class SeriesMetadata(_Frozen):
    """Descriptive, non-identifying metadata for a single DICOM series."""

    series_instance_uid: str
    study_instance_uid: str
    modality: str = Field(description="DICOM modality code, e.g. CT, MR, PT.")
    num_instances: int = Field(ge=0)
    rows: int | None = Field(default=None, ge=0)
    columns: int | None = Field(default=None, ge=0)
    pixel_spacing_mm: tuple[float, float] | None = None
    slice_thickness_mm: float | None = None
    manufacturer: str | None = None
    source_path: str | None = None


class IntensityStats(_Frozen):
    """Summary statistics of voxel intensities for a volume."""

    minimum: float
    maximum: float
    mean: float
    std: float


class QCReport(_Frozen):
    """Result of running quality-control checks on an ingested series."""

    series_instance_uid: str
    num_slices: int = Field(ge=0)
    spacing_consistent: bool
    geometry_consistent: bool
    intensity: IntensityStats | None = None
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        """True when no hard errors were recorded (warnings are non-blocking)."""
        return not self.errors


class DeidentificationResult(_Frozen):
    """Audit record describing what de-identification changed.

    For a pipeline run this is the union over every instance in the series. Element
    paths inside sequences are written ``Sequence[].Keyword``.
    """

    level: DeidentificationLevel
    removed_tags: tuple[str, ...]
    blanked_tags: tuple[str, ...]
    pseudonymised_patient_id: str | None = Field(
        default=None, description="The pseudonym, when the series maps to exactly one."
    )
    retained_safe_tags: tuple[str, ...] = ()
    instances: int = Field(default=1, ge=0, description="Instances this record covers.")
    replaced_uids: tuple[str, ...] = ()
    removed_private_tags: int = Field(default=0, ge=0)
    pseudonymised_patient_ids: tuple[str, ...] = ()


class PixelPrivacyReport(_Frozen):
    """What is known about identifying content in the pixel data of a series.

    Pixel data is never analysed or modified, so ``pixel_content_verified`` and
    ``pixels_modified`` are always False. ``status`` is ``"flagged"`` when metadata
    indicates known or suspected burned-in annotation, else ``"unverified"``. A
    missing or ``NO`` BurnedInAnnotation indicator is not proof of clean pixels.
    """

    status: Literal["flagged", "unverified"]
    policy: BurnedInPolicy
    instances: int = Field(ge=0)
    instances_flagged: int = Field(default=0, ge=0)
    reasons: tuple[str, ...] = Field(default=(), description="Reason codes, no values.")
    burned_in_annotation: dict[str, int] = Field(
        default_factory=dict,
        description="Instance counts per BurnedInAnnotation value: YES, NO, absent, other.",
    )
    pixels_modified: Literal[False] = False
    pixel_content_verified: Literal[False] = False


class ConversionResult(_Frozen):
    """Record of a volume successfully written to disk."""

    output_path: str
    output_format: OutputFormat
    shape: tuple[int, ...]
    spacing_mm: tuple[float, ...]
