"""DICOM de-identification.

Implements a documented subset of the DICOM PS3.15 Basic Application Level
Confidentiality Profile (Annex E); the full per-level policy is in
``docs/deidentification-policy.md``. Every level applies the core profile:

* direct identifiers and every person-name (PN) element are removed, at any depth
* identifying sequences and free-text comment fields are removed
* AccessionNumber and StudyID are blanked
* all private tags are removed
* every instance UID is replaced with a keyed ``2.25`` UID (references stay consistent)
* PatientID is pseudonymised wherever it appears

Then:

* **basic** keeps dates ("Retain Longitudinal Temporal Information") and patient
  characteristics; remaining text that contains one of the dataset's own
  identifiers is blanked.
* **moderate** additionally blanks every date/time and removes device identifiers.
* **strict** additionally removes patient characteristics and blanks all remaining
  free text outside a geometry safe-list.

PatientID and UIDs are keyed with HMAC-SHA256, so the mapping is stable under one
secret and cannot be reversed without it: see :func:`resolve_pseudonym_secret`.

.. warning::
   De-identification is risk reduction, not a legal guarantee. Only header data is
   processed: burned-in pixel annotations are **not** removed. Free-text screening
   only catches this dataset's own known identifiers. Always review output before
   release outside a controlled environment.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
from collections.abc import Iterable
from dataclasses import dataclass, field

from pydicom.datadict import dictionary_has_tag, dictionary_VR
from pydicom.dataelem import DataElement
from pydicom.dataset import Dataset
from pydicom.tag import BaseTag

from .exceptions import ConfigurationError
from .models import DeidentificationLevel, DeidentificationResult
from .observability import get_logger

logger = get_logger(__name__)

# --- Policy tables (PS3.15 Annex E, Table E.1-1 actions noted) ------------------

# Removed at every level and every nesting depth (action X). Every PN element is
# removed too, whatever its keyword.
_REMOVE_ALWAYS: frozenset[str] = frozenset(
    {
        # Patient
        "PatientBirthDate",
        "PatientBirthTime",
        "PatientBirthName",
        "PatientAddress",
        "PatientTelephoneNumbers",
        "PatientMotherBirthName",
        "OtherPatientIDs",
        "OtherPatientNames",
        "OtherPatientIDsSequence",
        "IssuerOfPatientID",
        "MedicalRecordLocator",
        "MilitaryRank",
        "EthnicGroup",
        "Occupation",
        "PatientReligiousPreference",
        "CountryOfResidence",
        "RegionOfResidence",
        "ResponsibleOrganization",
        "PatientInsurancePlanCodeSequence",
        "ReferencedPatientSequence",
        "ReferencedPatientPhotoSequence",
        "AdditionalPatientHistory",
        "PatientComments",
        "PatientTelecomInformation",
        "PatientBirthDateInAlternativeCalendar",
        "PatientDeathDateInAlternativeCalendar",
        "PatientAlternativeCalendar",
        "CurrentPatientLocation",
        "PatientInstitutionResidence",
        "MedicalAlerts",
        "Allergies",
        # Contact details of any person (also inside sequences)
        "PersonAddress",
        "PersonTelephoneNumbers",
        "PersonTelecomInformation",
        # Staff and institution
        "ReferringPhysicianAddress",
        "ReferringPhysicianTelephoneNumbers",
        "ReferringPhysicianIdentificationSequence",
        "PhysiciansOfRecordIdentificationSequence",
        "PerformingPhysicianIdentificationSequence",
        "PhysiciansReadingStudyIdentificationSequence",
        "OperatorIdentificationSequence",
        "InstitutionName",
        "InstitutionAddress",
        "InstitutionalDepartmentName",
        "InstitutionCodeSequence",
        # Orders, visits and procedure steps
        "RequestAttributesSequence",
        "ReferencedStudySequence",
        "ReferencedPerformedProcedureStepSequence",
        "RequestedProcedureID",
        "RequestedProcedureDescription",
        "RequestedProcedureComments",
        "ImagingServiceRequestComments",
        "ScheduledProcedureStepID",
        "ScheduledProcedureStepDescription",
        "PerformedProcedureStepID",
        "PerformedProcedureStepDescription",
        "AdmissionID",
        "AdmittingDiagnosesDescription",
        "ServiceEpisodeID",
        "ServiceEpisodeDescription",
        # Free-text comments
        "ImageComments",
        "StudyComments",
        "AcquisitionComments",
        "InterpretationText",
    }
)

# Removed at MODERATE and above: device and location identifiers.
_REMOVE_MODERATE: frozenset[str] = frozenset(
    {
        "StationName",
        "DeviceSerialNumber",
        "DetectorID",
        "GantryID",
        "PerformedStationAETitle",
        "ScheduledStationAETitle",
    }
)

# Removed at STRICT: patient characteristics (the "Retain Patient Characteristics"
# option is applied at basic and moderate only).
_REMOVE_STRICT: frozenset[str] = frozenset({"PatientAge", "PatientSize", "PatientWeight"})

# Kept present but zero-length (action Z).
_BLANK_ALWAYS: frozenset[str] = frozenset({"AccessionNumber", "StudyID"})
_BLANK_STRICT: frozenset[str] = frozenset({"PatientSex"})

# UIDs that identify a class, syntax or implementation, not an instance or patient.
_KEEP_UID_KEYWORDS: frozenset[str] = frozenset(
    {
        "SOPClassUID",
        "MediaStorageSOPClassUID",
        "ReferencedSOPClassUID",
        "ReferencedSOPClassUIDInFile",
        "AffectedSOPClassUID",
        "RequestedSOPClassUID",
        "RelatedGeneralSOPClassUID",
        "OriginalSpecializedSOPClassUID",
        "TransferSyntaxUID",
        "ReferencedTransferSyntaxUIDInFile",
        "ImplementationClassUID",
        "CodingSchemeUID",
    }
)
# UIDs defined by the DICOM standard itself are never identifying.
_DICOM_UID_ROOT = "1.2.840.10008."

_DATE_VRS = frozenset({"DA", "DT", "TM"})
# Text VRs screened for known identifiers at basic/moderate.
_TEXT_VRS = frozenset({"LO", "SH", "ST", "LT", "UT", "UC"})
# VRs blanked wholesale at STRICT (outside the safe-list).
_STRICT_VRS = _TEXT_VRS | _DATE_VRS | {"AS"}

# Values collected before scrubbing and searched for in remaining free text.
_IDENTIFIER_KEYWORDS: frozenset[str] = frozenset(
    {
        "PatientID",
        "OtherPatientIDs",
        "IssuerOfPatientID",
        "AccessionNumber",
        "StudyID",
        "PatientBirthDate",
        "RequestedProcedureID",
        "AdmissionID",
        "MedicalRecordLocator",
        "InstitutionName",
    }
)
# Shorter name parts or IDs are too likely to match ordinary words.
_MIN_TOKEN_LENGTH = 3

# Clinically essential, non-identifying attributes STRICT never blanks.
_SAFE_LIST: tuple[str, ...] = (
    "Modality",
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

# --- Pseudonymisation secret ----------------------------------------------------

#: Environment variable holding the per-project pseudonymisation secret.
PSEUDONYM_SECRET_ENV = "DICOMFORGE_PSEUDONYM_SECRET"
#: Minimum secret length; shorter secrets are guessable.
MIN_SECRET_LENGTH = 16
# The default salt of dicom-forge <= 0.1.1. It is public, so anything hashed with it
# can be reversed by enumeration (audit 2026-10-26, finding V5).
_PUBLIC_LEGACY_SALT = "dicom-forge"

# Random key used when no secret is configured. Generated once per process so a
# series (and repeated runs in one session) stay consistent; never persisted.
_process_secret: str | None = None


def validate_pseudonym_secret(secret: str) -> str:
    """Return ``secret`` unchanged, or raise ConfigurationError if it is unsafe to use."""
    if secret == _PUBLIC_LEGACY_SALT:
        raise ConfigurationError(
            "The pseudonymisation secret 'dicom-forge' is public and makes pseudonyms "
            "reversible. Use a private random value."
        )
    if len(secret) < MIN_SECRET_LENGTH:
        raise ConfigurationError(
            f"The pseudonymisation secret must be at least {MIN_SECRET_LENGTH} characters."
        )
    return secret


def resolve_pseudonym_secret(explicit: str | None = None) -> str:
    """Pick the pseudonymisation secret: explicit, then environment, then ephemeral.

    With no secret configured, a random per-process key is used and a warning is
    logged: pseudonyms are then not reversible, but also not stable across sessions.
    The secret itself is never logged.
    """
    global _process_secret
    if explicit is not None:
        return validate_pseudonym_secret(explicit)
    from_env = os.environ.get(PSEUDONYM_SECRET_ENV)
    if from_env:
        return validate_pseudonym_secret(from_env)
    if _process_secret is None:
        _process_secret = secrets.token_hex(32)
        logger.warning(
            "No pseudonymisation secret configured; using a random key for this session. "
            "PatientID pseudonyms will differ between sessions. Set %s to a private "
            "value (>= %d characters) for stable pseudonyms.",
            PSEUDONYM_SECRET_ENV,
            MIN_SECRET_LENGTH,
        )
    return _process_secret


def pseudonymise(value: str, *, salt: str) -> str:
    """Return a deterministic pseudonym for an identifier, keyed by ``salt``.

    Uses HMAC-SHA256, so the pseudonym cannot be recomputed (or reversed by
    enumerating likely identifiers) without the secret.
    """
    digest = hmac.new(salt.encode(), value.encode(), hashlib.sha256).hexdigest()
    return f"DF-{digest[:16].upper()}"


def pseudonymise_uid(uid: str, *, salt: str) -> str:
    """Return a keyed replacement UID for ``uid`` under the ``2.25`` root.

    The ``2.25`` root (PS3.5 B.2) takes a 128-bit integer; here it is the first 128
    bits of HMAC-SHA256(salt, uid), so the mapping is consistent under one secret
    (references between instances keep resolving) and unlinkable without it.
    """
    digest = hmac.new(salt.encode(), uid.encode(), hashlib.sha256).hexdigest()
    return f"2.25.{int(digest[:32], 16)}"


# --- Scrubbing --------------------------------------------------------------------


@dataclass
class _Scrub:
    """Per-dataset state and findings while walking the element tree."""

    level: DeidentificationLevel
    secret: str
    pseudonymise_patient_id: bool
    tokens: frozenset[str]
    removed: list[str] = field(default_factory=list)
    blanked: list[str] = field(default_factory=list)
    replaced_uids: list[str] = field(default_factory=list)
    private_removed: int = 0
    patient_ids: set[str] = field(default_factory=set)

    @property
    def moderate(self) -> bool:
        return self.level is not DeidentificationLevel.BASIC

    @property
    def strict(self) -> bool:
        return self.level is DeidentificationLevel.STRICT


def _walk(ds: Dataset) -> Iterable[DataElement]:
    for elem in ds:
        yield elem
        if elem.VR == "SQ":
            for item in elem.value:
                yield from _walk(item)


def _values(elem: DataElement) -> list[str]:
    return [str(v) for v in elem.value] if elem.VM > 1 else [str(elem.value)]


def _is_person_name(elem: DataElement) -> bool:
    """PN by actual VR, or by dictionary VR when the element arrived as UN."""
    if elem.VR == "PN":
        return True
    return dictionary_has_tag(elem.tag) and dictionary_VR(elem.tag) == "PN"


def _is_overlay_or_curve(tag: BaseTag) -> bool:
    """Repeating groups 50xx (curves, retired) and 60xx (overlays): PS3.15 action X."""
    group = tag.group
    return group % 2 == 0 and (0x5000 <= group <= 0x501E or 0x6000 <= group <= 0x601E)


def _is_instance_uid(elem: DataElement, value: str) -> bool:
    return (
        elem.VR == "UI"
        and elem.keyword not in _KEEP_UID_KEYWORDS
        and not value.startswith(_DICOM_UID_ROOT)
    )


def _identifier_tokens(ds: Dataset, *, include_dates: bool) -> frozenset[str]:
    """Known identifying strings in ``ds`` (upper-cased), collected before scrubbing.

    Names, IDs, the original instance UIDs, and (when dates are being removed) the
    dataset's own date values, so that copies quoted in free text are caught too.
    """
    tokens: set[str] = set()
    for elem in _walk(ds):
        if elem.tag.is_private or elem.value in (None, "") or elem.VR == "SQ":
            continue
        if _is_person_name(elem):
            raw = (
                elem.value.decode(errors="ignore") if isinstance(elem.value, bytes) else elem.value
            )
            parts = re.split(r"[\^=\s]+", str(raw))
        elif elem.keyword in _IDENTIFIER_KEYWORDS:
            parts = _values(elem)
        elif elem.VR == "UI":
            parts = [v for v in _values(elem) if _is_instance_uid(elem, v)]
        elif include_dates and elem.VR in ("DA", "DT"):
            parts = [v[:8] for v in _values(elem)]  # the YYYYMMDD part
        else:
            continue
        tokens.update(p.strip().upper() for p in parts if len(p.strip()) >= _MIN_TOKEN_LENGTH)
    return frozenset(tokens)


def _blank(elem: DataElement, path: str, st: _Scrub) -> None:
    if elem.value not in (None, ""):
        elem.value = ""
        st.blanked.append(path)


def _replace_uid_element(elem: DataElement, path: str, st: _Scrub) -> None:
    if elem.keyword in _KEEP_UID_KEYWORDS or elem.value in (None, ""):
        return

    def swap(value: object) -> str:
        uid = str(value)
        if not uid or uid.startswith(_DICOM_UID_ROOT):
            return uid
        return pseudonymise_uid(uid, salt=st.secret)

    new = [swap(v) for v in elem.value] if elem.VM > 1 else swap(elem.value)
    if new != elem.value:
        elem.value = new
        st.replaced_uids.append(path)


def _scrub(ds: Dataset, st: _Scrub, prefix: str = "") -> None:
    """Apply the policy to every element of ``ds``, recursing into sequences."""
    for elem in list(ds):
        kw = elem.keyword
        path = f"{prefix}{kw or elem.tag}"
        if elem.tag.is_private:
            del ds[elem.tag]
            st.private_removed += 1
        elif (
            kw in _REMOVE_ALWAYS
            or _is_person_name(elem)
            or _is_overlay_or_curve(elem.tag)
            # Public tags outside the DICOM dictionary can't be interpreted or checked.
            or not dictionary_has_tag(elem.tag)
            or (st.moderate and (kw in _REMOVE_MODERATE or elem.VR == "AE"))
            or (st.strict and kw in _REMOVE_STRICT)
        ):
            del ds[elem.tag]
            st.removed.append(path)
        elif elem.VR == "SQ":
            for item in elem.value:
                _scrub(item, st, f"{path}[].")
        elif kw == "PatientID":
            if st.pseudonymise_patient_id and elem.value:
                elem.value = pseudonymise(str(elem.value), salt=st.secret)
                st.patient_ids.add(elem.value)
            elif st.strict:
                _blank(elem, path, st)
        elif elem.VR == "UI":
            _replace_uid_element(elem, path, st)
        elif _blank_by_policy(elem, st):
            _blank(elem, path, st)


def _blank_by_policy(elem: DataElement, st: _Scrub) -> bool:
    """True for elements this level keeps present but empties (action Z)."""
    kw = elem.keyword
    if kw in _BLANK_ALWAYS or (st.strict and kw in _BLANK_STRICT):
        return True
    if st.moderate and elem.VR in _DATE_VRS:
        return True
    if st.strict and elem.VR in _STRICT_VRS and kw not in _SAFE_LIST:
        return True
    return elem.VR in _TEXT_VRS and _mentions_identifier(elem.value, st.tokens)


def _mentions_identifier(value: object, tokens: frozenset[str]) -> bool:
    if value in (None, "") or not tokens:
        return False
    text = str(value).upper()
    return any(token in text for token in tokens)


def deidentify_dataset(
    ds: Dataset,
    *,
    level: DeidentificationLevel = DeidentificationLevel.MODERATE,
    pseudonymise_patient_id: bool = True,
    salt: str | None = None,
) -> DeidentificationResult:
    """De-identify a single dataset **in place** and return an audit record.

    ``salt`` is the pseudonymisation secret for PatientID and UIDs; when None it is
    resolved by :func:`resolve_pseudonym_secret`.
    """
    st = _Scrub(
        level=level,
        secret=resolve_pseudonym_secret(salt),
        pseudonymise_patient_id=pseudonymise_patient_id,
        tokens=_identifier_tokens(ds, include_dates=level is not DeidentificationLevel.BASIC),
    )
    _scrub(ds, st)
    file_meta = getattr(ds, "file_meta", None)
    if file_meta is not None:
        for elem in list(file_meta):
            path = f"file_meta.{elem.keyword}"
            if elem.VR == "UI":
                _replace_uid_element(elem, path, st)
            elif elem.VR == "AE" and st.moderate:  # source/sending station AE titles
                del file_meta[elem.tag]
                st.removed.append(path)

    # Provenance (PS3.15 E.1.1). PatientIdentityRemoved covers the attributes *and* the
    # pixel data. Pixels are never analysed, so the software cannot assert YES; the
    # method records what was actually done. BurnedInAnnotation is left as declared.
    ds.PatientIdentityRemoved = "NO"
    ds.DeidentificationMethod = (
        f"dicom-forge {level.value}: header de-identified; pixels unverified"
    )
    ds.LongitudinalTemporalInformationModified = "REMOVED" if st.moderate else "UNMODIFIED"

    ids = tuple(sorted(st.patient_ids))
    result = DeidentificationResult(
        level=level,
        removed_tags=tuple(dict.fromkeys(st.removed)),
        blanked_tags=tuple(dict.fromkeys(st.blanked)),
        pseudonymised_patient_id=ids[0] if len(ids) == 1 else None,
        retained_safe_tags=_SAFE_LIST,
        instances=1,
        replaced_uids=tuple(dict.fromkeys(st.replaced_uids)),
        removed_private_tags=st.private_removed,
        pseudonymised_patient_ids=ids,
    )
    logger.debug(
        "De-identified dataset: removed=%d blanked=%d uids=%d private=%d level=%s",
        len(result.removed_tags),
        len(result.blanked_tags),
        len(result.replaced_uids),
        result.removed_private_tags,
        level.value,
    )
    return result


def combine_results(results: list[DeidentificationResult]) -> DeidentificationResult:
    """Merge per-instance records into one record for the whole series."""
    if not results:
        raise ValueError("combine_results needs at least one record.")

    def union(attr: str) -> tuple[str, ...]:
        return tuple(dict.fromkeys(tag for r in results for tag in getattr(r, attr)))

    ids = tuple(sorted({pid for r in results for pid in r.pseudonymised_patient_ids}))
    return DeidentificationResult(
        level=results[0].level,
        removed_tags=union("removed_tags"),
        blanked_tags=union("blanked_tags"),
        pseudonymised_patient_id=ids[0] if len(ids) == 1 else None,
        retained_safe_tags=results[0].retained_safe_tags,
        instances=sum(r.instances for r in results),
        replaced_uids=union("replaced_uids"),
        removed_private_tags=sum(r.removed_private_tags for r in results),
        pseudonymised_patient_ids=ids,
    )
