"""DICOM de-identification.

Implements a pragmatic subset of the DICOM PS3.15 Basic Application Level
Confidentiality Profile. Three escalating levels let callers trade analytic
fidelity (e.g. keeping acquisition dates for longitudinal studies) against
disclosure risk. PatientID is pseudonymised with a salted SHA-256 hash so the
same patient maps to the same pseudonym within a project but cannot be reversed.

.. warning::
   De-identification is risk reduction, not a legal guarantee. Pixel-data burned-in
   annotations and private vendor tags can still carry PHI. Always review output
   before release outside a controlled environment.
"""

from __future__ import annotations

import hashlib

from pydicom.dataset import Dataset

from .models import DeidentificationLevel, DeidentificationResult
from .observability import get_logger

logger = get_logger(__name__)

# Direct identifiers removed at every level (PS3.15 Basic Profile core).
_ALWAYS_REMOVE: tuple[str, ...] = (
    "PatientName",
    "PatientBirthDate",
    "PatientBirthTime",
    "PatientAddress",
    "PatientTelephoneNumbers",
    "PatientMotherBirthName",
    "OtherPatientIDs",
    "OtherPatientNames",
    "ReferringPhysicianName",
    "ReferringPhysicianTelephoneNumbers",
    "PerformingPhysicianName",
    "OperatorsName",
    "InstitutionName",
    "InstitutionAddress",
    "InstitutionalDepartmentName",
    "RequestingPhysician",
    "NameOfPhysiciansReadingStudy",
    "MilitaryRank",
    "EthnicGroup",
    "Occupation",
    "AdditionalPatientHistory",
    "PatientComments",
)

# Removed at MODERATE and above: device/location identifiers.
_REMOVE_MODERATE: tuple[str, ...] = (
    "StationName",
    "DeviceSerialNumber",
    "DetectorID",
    "GantryID",
    "PerformedStationAETitle",
    "ScheduledStationAETitle",
)

# Date/time tags shifted-to-blank at MODERATE and above.
_DATE_TAGS: tuple[str, ...] = (
    "StudyDate",
    "SeriesDate",
    "AcquisitionDate",
    "ContentDate",
    "StudyTime",
    "SeriesTime",
    "AcquisitionTime",
    "ContentTime",
)

# Clinically essential tags never removed (the "safe list").
_SAFE_LIST: tuple[str, ...] = (
    "Modality",
    "SeriesInstanceUID",
    "StudyInstanceUID",
    "SOPInstanceUID",
    "Rows",
    "Columns",
    "PixelSpacing",
    "SliceThickness",
    "ImagePositionPatient",
    "ImageOrientationPatient",
    "RescaleSlope",
    "RescaleIntercept",
    "PixelData",
)


def pseudonymise(value: str, *, salt: str) -> str:
    """Return a deterministic, non-reversible pseudonym for an identifier."""
    digest = hashlib.sha256(f"{salt}:{value}".encode()).hexdigest()
    return f"DF-{digest[:16].upper()}"


def _tags_for_level(level: DeidentificationLevel) -> tuple[list[str], list[str]]:
    """Return (tags_to_remove, date_tags_to_blank) for a level."""
    remove = list(_ALWAYS_REMOVE)
    blank_dates: list[str] = []
    if level in (DeidentificationLevel.MODERATE, DeidentificationLevel.STRICT):
        remove += list(_REMOVE_MODERATE)
        blank_dates = list(_DATE_TAGS)
    return remove, blank_dates


def deidentify_dataset(
    ds: Dataset,
    *,
    level: DeidentificationLevel = DeidentificationLevel.MODERATE,
    pseudonymise_patient_id: bool = True,
    salt: str = "dicom-forge",
) -> DeidentificationResult:
    """De-identify a single dataset **in place** and return an audit record."""
    remove_tags, blank_dates = _tags_for_level(level)

    removed: list[str] = []
    blanked: list[str] = []

    for keyword in remove_tags:
        if keyword in ds:
            delattr(ds, keyword)
            removed.append(keyword)

    for keyword in blank_dates:
        if keyword in ds and getattr(ds, keyword):
            setattr(ds, keyword, "")
            blanked.append(keyword)

    pseudonym: str | None = None
    if pseudonymise_patient_id and "PatientID" in ds and ds.PatientID:
        pseudonym = pseudonymise(str(ds.PatientID), salt=salt)
        ds.PatientID = pseudonym

    if level is DeidentificationLevel.STRICT:
        # Blank every non-safe, non-binary string/UI element we did not explicitly keep.
        for elem in list(ds):
            kw = elem.keyword
            if not kw or kw in _SAFE_LIST or kw in removed or kw in blanked:
                continue
            if kw == "PatientID":
                continue
            if elem.VR in {"PN", "LO", "SH", "ST", "LT", "UT", "DA", "TM", "DT"}:
                setattr(ds, kw, "")
                blanked.append(kw)

    # Annotate provenance so downstream consumers know data was processed.
    ds.PatientIdentityRemoved = "YES"
    ds.DeidentificationMethod = f"dicom-forge {level.value}"

    result = DeidentificationResult(
        level=level,
        removed_tags=tuple(removed),
        blanked_tags=tuple(dict.fromkeys(blanked)),  # de-dup, preserve order
        pseudonymised_patient_id=pseudonym,
        retained_safe_tags=_SAFE_LIST,
    )
    logger.debug(
        "De-identified dataset: removed=%d blanked=%d level=%s",
        len(result.removed_tags),
        len(result.blanked_tags),
        level.value,
    )
    return result
