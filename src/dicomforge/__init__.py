"""dicom-forge: an enterprise medical-imaging pipeline.

Ingest DICOM, de-identify PHI, run quality control, and convert to the formats
3D Slicer and ITK-SNAP load natively (NIfTI, NRRD, and Slicer ``.seg.nrrd``).

The public API is re-exported here so consumers can ``from dicomforge import ...``
without depending on the internal module layout.
"""

from __future__ import annotations

from ._version import __version__
from .config import PipelineConfig
from .convert import convert_series
from .deidentify import deidentify_dataset, pseudonymise
from .exceptions import (
    ConversionError,
    DeidentificationError,
    DicomForgeError,
    IngestionError,
    MissingDependencyError,
    QualityControlError,
)
from .ingest import DicomSeries, load_series
from .models import (
    ConversionResult,
    DeidentificationLevel,
    DeidentificationResult,
    OutputFormat,
    QCReport,
    SeriesMetadata,
)
from .pipeline import PipelineResult, run_pipeline
from .qc import run_qc
from .segmentation import write_labelmap

__all__ = [
    "__version__",
    # Pipeline
    "run_pipeline",
    "PipelineResult",
    "PipelineConfig",
    # Stages
    "load_series",
    "DicomSeries",
    "deidentify_dataset",
    "pseudonymise",
    "run_qc",
    "convert_series",
    "write_labelmap",
    # Models
    "SeriesMetadata",
    "QCReport",
    "DeidentificationResult",
    "DeidentificationLevel",
    "ConversionResult",
    "OutputFormat",
    # Errors
    "DicomForgeError",
    "IngestionError",
    "DeidentificationError",
    "ConversionError",
    "QualityControlError",
    "MissingDependencyError",
]
