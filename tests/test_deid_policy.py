"""Regression tests for the PS3.15-aligned de-identification policy.

Audit 2026-10-26 findings covered here:
  V3  identifiers in free text           V8  AccessionNumber kept (basic/moderate)
  V9/V10 UIDs never replaced             V11 private tags kept
  V12 sequences never traversed          V13 only 8 date tags blanked
  V14 strict skipped AS/sequences/etc.   V6  strict kept a raw PatientID
  V24 audit reflected only the last slice

All identifying values are fictional.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pydicom
import pytest
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.sequence import Sequence
from pydicom.uid import ExplicitVRLittleEndian, MRImageStorage

from _dicomio import save_dicom
from dicomforge.config import PipelineConfig
from dicomforge.deidentify import deidentify_dataset
from dicomforge.models import DeidentificationLevel
from dicomforge.pipeline import run_pipeline

ENV = "DICOMFORGE_PSEUDONYM_SECRET"
SECRET = "policy-test-secret-0123456789abcd"
LEVELS = list(DeidentificationLevel)
BASIC, MODERATE, STRICT = (
    DeidentificationLevel.BASIC,
    DeidentificationLevel.MODERATE,
    DeidentificationLevel.STRICT,
)

ROOT = "1.2.826.0.1.3680043.8.498.77"
STUDY_UID = f"{ROOT}.1"
SERIES_UID = f"{ROOT}.2"
FOR_UID = f"{ROOT}.3"
SOP_UIDS = [f"{ROOT}.10{i}" for i in range(3)]

CANARIES = {
    "name": "TEST^PATIENT",
    "id": "TEST-12345",
    "alt_id": "TEST-ALT-999",
    "accession": "ACC-TEST-0001",
    "birth": "19010203",
    "institution": "FICTIONAL GENERAL HOSPITAL",
    "doctor": "TEST^DOCTOR",
    "nested_doctor": "NESTED^PHYSICIAN",
    "issuer": "FICTIONAL MRN ISSUER",
    "rp_id": "RP-TEST-01",
    "private": "PRIVATE-CANARY",
    "nested_private": "NESTED-PRIVATE-CANARY",
    "study_id": "TESTSTUDY01",
}
UID_2_25 = re.compile(r"^2\.25\.(0|[1-9][0-9]*)$")


def make_slice(i: int) -> Dataset:
    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = MRImageStorage
    meta.MediaStorageSOPInstanceUID = SOP_UIDS[i]
    meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = Dataset()
    ds.file_meta = meta
    ds.SOPClassUID = MRImageStorage
    ds.SOPInstanceUID = SOP_UIDS[i]
    ds.StudyInstanceUID = STUDY_UID
    ds.SeriesInstanceUID = SERIES_UID
    ds.FrameOfReferenceUID = FOR_UID
    ds.Modality = "MR"
    ds.Manufacturer = "FictionalVendor"
    ds.InstanceNumber = i + 1

    ds.PatientName = CANARIES["name"]
    ds.PatientID = CANARIES["id"]
    ds.IssuerOfPatientID = CANARIES["issuer"]
    ds.PatientBirthDate = CANARIES["birth"]
    ds.PatientSex = "O"
    ds.PatientAge = "077Y"
    ds.PatientWeight = "77.7"
    ds.PatientSize = "1.77"
    ds.AccessionNumber = CANARIES["accession"]
    ds.StudyID = CANARIES["study_id"]
    ds.InstitutionName = CANARIES["institution"]
    ds.ReferringPhysicianName = CANARIES["doctor"]
    ds.StationName = "TEST-STATION-01"
    ds.DeviceSerialNumber = "TEST-SN-0001"

    ds.StudyDate = "20990315"
    ds.StudyTime = "101010"
    ds.InstanceCreationDate = "20990316"
    ds.AcquisitionDateTime = "20990315101010"

    ds.StudyDescription = f"BRAIN FOLLOWUP {CANARIES['id']}"
    ds.SeriesDescription = "T1 AXIAL"
    ds.ProtocolName = "Scan for PATIENT protocol"  # contains a name component
    ds.ImageComments = "Free-text comment"
    ds.BodyPartExamined = "BRAIN"

    other = Dataset()
    other.PatientID = CANARIES["alt_id"]
    other.IssuerOfPatientID = CANARIES["issuer"]
    ds.OtherPatientIDsSequence = Sequence([other])

    req = Dataset()
    req.AccessionNumber = CANARIES["accession"]
    req.RequestedProcedureID = CANARIES["rp_id"]
    ds.RequestAttributesSequence = Sequence([req])

    # Two levels of nesting, not in any removal list: identifiers must still go.
    person = Dataset()
    person.PersonName = CANARIES["nested_doctor"]
    person.PersonIdentificationCodeSequence = Sequence([])
    step = Dataset()
    step.PerformedProcedureStepStartDate = "20990315"
    step.ContentSequence = Sequence([person])
    nested_block = step.private_block(0x0013, "FICTIONAL_NESTED", create=True)
    nested_block.add_new(0x01, "LO", CANARIES["nested_private"])
    ds.PerformedProtocolCodeSequence = Sequence([step])

    # Cross-instance reference: slice i points at the next slice.
    ref = Dataset()
    ref.ReferencedSOPClassUID = MRImageStorage
    ref.ReferencedSOPInstanceUID = SOP_UIDS[(i + 1) % 3]
    ds.ReferencedImageSequence = Sequence([ref])

    block = ds.private_block(0x0011, "FICTIONAL_VENDOR", create=True)
    block.add_new(0x01, "LO", CANARIES["private"])
    block.add_new(0x02, "DA", CANARIES["birth"])

    if i == 0:  # present only on the first slice in sorted order (V24)
        ds.AdditionalPatientHistory = "History on first slice only"

    ds.Rows = ds.Columns = 8
    ds.PixelSpacing = [0.9, 0.9]
    ds.SliceThickness = 3.0
    ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
    ds.ImagePositionPatient = [0.0, 0.0, i * 3.0]
    ds.RescaleSlope, ds.RescaleIntercept = 1, 0
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.BitsAllocated = ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 1
    ds.PixelData = (np.arange(64, dtype=np.int16).reshape(8, 8) + i).tobytes()
    return ds


def walk_all(ds: Dataset, prefix: str = "") -> Iterator[tuple[str, pydicom.DataElement]]:
    """Every element, recursively, including file meta."""
    if not prefix and getattr(ds, "file_meta", None) is not None:
        for e in ds.file_meta:
            yield f"file_meta.{e.keyword}", e
    for e in ds:
        path = f"{prefix}{e.keyword or e.tag}"
        yield path, e
        if e.VR == "SQ":
            for item in e.value:
                yield from walk_all(item, f"{path}[].")


def surviving_canaries(ds: Dataset) -> dict[str, str]:
    originals = {STUDY_UID, SERIES_UID, FOR_UID, *SOP_UIDS}
    found = {}
    for path, e in walk_all(ds):
        if e.tag == 0x7FE00010 or e.VR == "SQ":
            continue
        text = str(e.value)
        for label, value in CANARIES.items():
            if value in text:
                found[path] = label
        if any(uid in text for uid in originals):
            found[path] = "original-uid"
    return found


@pytest.fixture(autouse=True)
def _secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV, SECRET)


@pytest.fixture
def slices() -> list[Dataset]:
    return [make_slice(i) for i in range(3)]


def deid(ds: Dataset, level: DeidentificationLevel, **kw):
    return deidentify_dataset(ds, level=level, salt=SECRET, **kw)


# -- whole-tree canary scan (reproduces the audit's central finding) -----------


@pytest.mark.parametrize("level", LEVELS)
def test_no_identifier_survives_anywhere(slices: list[Dataset], level) -> None:
    for ds in slices:
        deid(ds, level)
        assert surviving_canaries(ds) == {}


# -- accession / study id (V8) ---------------------------------------------------


@pytest.mark.parametrize("level", LEVELS)
def test_accession_and_study_id_blanked(slices: list[Dataset], level) -> None:
    ds = slices[0]
    deid(ds, level)
    assert ds.AccessionNumber == ""
    assert ds.StudyID == ""
    assert "RequestAttributesSequence" not in ds


# -- private tags (V11) ----------------------------------------------------------


@pytest.mark.parametrize("level", LEVELS)
def test_all_private_tags_removed_recursively(slices: list[Dataset], level) -> None:
    ds = slices[0]
    result = deid(ds, level)
    private = [path for path, e in walk_all(ds) if e.tag.is_private]
    assert private == []
    assert result.removed_private_tags == 5  # 2 creators + 3 data elements


# -- UIDs (V9, V10) ----------------------------------------------------------------


@pytest.mark.parametrize("level", LEVELS)
def test_instance_uids_replaced_everywhere(slices: list[Dataset], level) -> None:
    ds = slices[0]
    deid(ds, level)
    for path, e in walk_all(ds):
        if e.VR != "UI":
            continue
        values = e.value if isinstance(e.value, list) else [e.value]
        for v in values:
            assert str(v).startswith("1.2.840.10008.") or UID_2_25.match(str(v)), (path, v)
    assert ds.SOPClassUID == MRImageStorage
    assert ds.ReferencedImageSequence[0].ReferencedSOPClassUID == MRImageStorage
    assert ds.file_meta.TransferSyntaxUID == ExplicitVRLittleEndian


def test_uid_mapping_consistent_across_series(slices: list[Dataset]) -> None:
    for ds in slices:
        deid(ds, MODERATE)
    a, b, c = slices
    assert a.SeriesInstanceUID != SERIES_UID and a.SOPInstanceUID not in SOP_UIDS
    assert a.StudyInstanceUID == b.StudyInstanceUID == c.StudyInstanceUID
    assert a.SeriesInstanceUID == b.SeriesInstanceUID == c.SeriesInstanceUID
    assert a.FrameOfReferenceUID == b.FrameOfReferenceUID
    assert len({a.SOPInstanceUID, b.SOPInstanceUID, c.SOPInstanceUID}) == 3
    # References still resolve: slice i points at slice i+1.
    assert a.ReferencedImageSequence[0].ReferencedSOPInstanceUID == b.SOPInstanceUID
    assert c.ReferencedImageSequence[0].ReferencedSOPInstanceUID == a.SOPInstanceUID
    for ds in slices:
        assert ds.file_meta.MediaStorageSOPInstanceUID == ds.SOPInstanceUID
    assert a.StudyInstanceUID != a.SeriesInstanceUID


def test_uid_mapping_depends_on_secret() -> None:
    x, y = make_slice(0), make_slice(0)
    deidentify_dataset(x, salt=SECRET)
    deidentify_dataset(y, salt="another-project-secret-000000")
    assert x.SeriesInstanceUID != y.SeriesInstanceUID


# -- nested sequences (V12) --------------------------------------------------------


@pytest.mark.parametrize("level", LEVELS)
def test_nested_identifiers_removed(slices: list[Dataset], level) -> None:
    ds = slices[0]
    deid(ds, level)
    assert "OtherPatientIDsSequence" not in ds
    step = ds.PerformedProtocolCodeSequence[0]
    person = step.ContentSequence[0]  # in no removal list: caught by the PN rule
    assert "PersonName" not in person


@pytest.mark.parametrize("level", LEVELS)
def test_nested_patient_id_pseudonymised(level) -> None:
    ds = make_slice(0)
    nested = Dataset()
    nested.PatientID = CANARIES["id"]
    ds.SourceImageSequence = Sequence([nested])
    deid(ds, level)
    assert ds.SourceImageSequence[0].PatientID == ds.PatientID != CANARIES["id"]


# -- free text (V3) ------------------------------------------------------------------


@pytest.mark.parametrize("level", [BASIC, MODERATE])
def test_free_text_screened_for_known_identifiers(slices: list[Dataset], level) -> None:
    ds = slices[0]
    deid(ds, level)
    assert ds.StudyDescription == ""  # contained the PatientID
    assert ds.ProtocolName == ""  # contained a PatientName component
    assert ds.SeriesDescription == "T1 AXIAL"  # nothing identifying: kept
    assert ds.BodyPartExamined == "BRAIN"
    assert "ImageComments" not in ds


def test_strict_blanks_all_free_text(slices: list[Dataset]) -> None:
    ds = slices[0]
    deid(ds, STRICT)
    assert ds.SeriesDescription == ""
    assert ds.StudyDescription == ""
    assert ds.Manufacturer == ""


# -- dates (V13) -------------------------------------------------------------------


def test_basic_retains_dates(slices: list[Dataset]) -> None:
    ds = slices[0]
    deid(ds, BASIC)
    assert ds.StudyDate == "20990315"
    assert ds.InstanceCreationDate == "20990316"
    assert ds.LongitudinalTemporalInformationModified == "UNMODIFIED"


@pytest.mark.parametrize("level", [MODERATE, STRICT])
def test_all_dates_blanked_recursively(slices: list[Dataset], level) -> None:
    ds = slices[0]
    deid(ds, level)
    dated = [
        path for path, e in walk_all(ds) if e.VR in ("DA", "DT", "TM") and e.value not in ("", None)
    ]
    assert dated == []
    assert ds.LongitudinalTemporalInformationModified == "REMOVED"


# -- patient characteristics, strict extras (V14, V6) -------------------------------


@pytest.mark.parametrize("level", [BASIC, MODERATE])
def test_patient_characteristics_retained(slices: list[Dataset], level) -> None:
    ds = slices[0]
    deid(ds, level)
    assert (ds.PatientAge, ds.PatientSex, str(ds.PatientWeight)) == ("077Y", "O", "77.7")


def test_strict_removes_patient_characteristics(slices: list[Dataset]) -> None:
    ds = slices[0]
    deid(ds, STRICT)
    for kw in ("PatientAge", "PatientWeight", "PatientSize"):
        assert kw not in ds
    assert ds.PatientSex == ""


def test_strict_never_keeps_raw_patient_id(slices: list[Dataset]) -> None:
    ds = slices[0]
    deid(ds, STRICT, pseudonymise_patient_id=False)
    assert CANARIES["id"] not in str(ds.get("PatientID", ""))


def test_strict_keeps_geometry_and_pixels(slices: list[Dataset]) -> None:
    ds = slices[0]
    before = ds.PixelData
    deid(ds, STRICT)
    assert ds.PixelData == before
    assert list(ds.ImagePositionPatient) == [0.0, 0.0, 0.0]
    assert ds.Modality == "MR" and ds.Rows == 8


# -- audit aggregation (V24) and the pipeline --------------------------------------


@pytest.fixture
def series_dir(tmp_path: Path) -> Path:
    d = tmp_path / "series"
    d.mkdir()
    for i in range(3):
        save_dicom(make_slice(i), d / f"s{i}.dcm")
    return d


def _hashes(d: Path) -> dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in d.iterdir()}


@pytest.mark.requires_convert
def test_audit_covers_whole_series(series_dir: Path, tmp_path: Path) -> None:
    result = run_pipeline(series_dir, tmp_path / "out" / "v")
    deid_record = result.deidentification
    assert deid_record is not None
    assert deid_record.instances == 3
    # Only the first slice in sorted order had AdditionalPatientHistory.
    assert "AdditionalPatientHistory" in deid_record.removed_tags
    assert deid_record.removed_private_tags == 15
    assert len(deid_record.pseudonymised_patient_ids) == 1
    assert deid_record.pseudonymised_patient_id == deid_record.pseudonymised_patient_ids[0]


@pytest.mark.requires_convert
@pytest.mark.parametrize("level", LEVELS)
def test_pipeline_geometry_conversion_and_source_intact(
    series_dir: Path, tmp_path: Path, level
) -> None:
    import SimpleITK as sitk

    before = _hashes(series_dir)
    plain = run_pipeline(
        series_dir, tmp_path / "plain" / "v", config=PipelineConfig(deidentify=False)
    )
    deid_run = run_pipeline(
        series_dir, tmp_path / "deid" / "v", config=PipelineConfig(deidentification_level=level)
    )
    assert _hashes(series_dir) == before
    assert deid_run.qc.passed and deid_run.qc.num_slices == 3
    assert deid_run.conversion is not None and plain.conversion is not None
    a = sitk.ReadImage(plain.conversion.output_path)
    b = sitk.ReadImage(deid_run.conversion.output_path)
    assert np.array_equal(sitk.GetArrayFromImage(a), sitk.GetArrayFromImage(b))
    assert a.GetSpacing() == b.GetSpacing() and a.GetOrigin() == b.GetOrigin()
    assert a.GetDirection() == b.GetDirection()


@pytest.mark.requires_convert
def test_audit_uids_match_dataset_uids(series_dir: Path, tmp_path: Path) -> None:
    """The audit record now reports the same replacement UIDs as the data."""
    from dicomforge.deidentify import pseudonymise_uid

    result = run_pipeline(series_dir, tmp_path / "out" / "v")
    assert result.metadata.series_instance_uid == pseudonymise_uid(SERIES_UID, salt=SECRET)
    assert result.metadata.study_instance_uid == pseudonymise_uid(STUDY_UID, salt=SECRET)
