"""Adversarial regression tests from the Phase 7 privacy review (all values fictional).

Each test hides an identifier somewhere the 0.2.0 policy did not reach:
overlay/curve groups, a PN stored with VR UN, unknown public tags, identifying
attributes missing from the removal list, AE titles, original UIDs and dates quoted
in free text. The last block checks that converted volumes say what was (not) done.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pydicom
import pytest
from pydicom.datadict import dictionary_has_tag
from pydicom.dataset import Dataset
from pydicom.sequence import Sequence

from _dicomio import save_dicom
from conftest import _make_slice
from dicomforge.config import PipelineConfig
from dicomforge.deidentify import deidentify_dataset
from dicomforge.models import DeidentificationLevel
from dicomforge.pipeline import run_pipeline

SECRET = "adversarial-test-secret-0123456789"
LEVELS = list(DeidentificationLevel)
BASIC, MODERATE, STRICT = LEVELS
NAME, PID = "TEST^PATIENT", "TEST-12345"


def walk(ds: Dataset) -> Iterator[pydicom.DataElement]:
    if getattr(ds, "file_meta", None) is not None:
        yield from ds.file_meta
    for elem in ds:
        yield elem
        if elem.VR == "SQ":
            for item in elem.value:
                yield from walk(item)


def text_of(ds: Dataset) -> str:
    return "\n".join(repr(e.value) for e in walk(ds) if e.VR != "SQ" and e.tag != 0x7FE00010)


def slice_ds() -> Dataset:
    ds = _make_slice(
        study_uid="1.2.826.0.1.3680043.8.498.55.1",
        series_uid="1.2.826.0.1.3680043.8.498.55.2",
        index=0,
        z=0.0,
    )
    ds.PatientName = NAME
    ds.PatientID = PID
    return ds


@pytest.fixture(autouse=True)
def _secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DICOMFORGE_PSEUDONYM_SECRET", SECRET)


# -- A: overlays and curves -------------------------------------------------------


@pytest.mark.parametrize("level", LEVELS)
def test_overlay_and_curve_groups_removed(level) -> None:
    ds = slice_ds()
    ds.add_new(0x60000010, "US", 16)  # OverlayRows
    ds.add_new(0x60000011, "US", 16)  # OverlayColumns
    ds.add_new(0x60000040, "CS", "G")  # OverlayType
    ds.add_new(0x60000050, "SS", [1, 1])  # OverlayOrigin
    ds.add_new(0x60000100, "US", 1)  # OverlayBitsAllocated
    ds.add_new(0x60000102, "US", 0)  # OverlayBitPosition
    ds.add_new(0x60000022, "LO", f"Label for {NAME}")  # OverlayDescription
    ds.add_new(0x60001500, "LO", PID)  # OverlayLabel
    ds.add_new(0x60003000, "OW", np.ones(32, dtype=np.uint8).tobytes())  # OverlayData
    ds.add_new(0x50000022, "LO", f"Curve of {NAME}")  # CurveDescription (retired)
    ds.add_new(0x50003000, "OW", b"\x00\x01" * 8)  # CurveData (retired)
    result = deidentify_dataset(ds, level=level, salt=SECRET)
    repeating = {*range(0x5000, 0x5020, 2), *range(0x6000, 0x6020, 2)}
    assert [e.tag for e in ds if e.tag.group in repeating] == []
    assert any("Overlay" in t or t.startswith("(6000") for t in result.removed_tags)


# -- B/C: VR UN and unknown public tags -----------------------------------------------


@pytest.mark.parametrize("level", LEVELS)
def test_person_name_with_vr_un_removed(level) -> None:
    ds = slice_ds()
    del ds.PatientName
    ds.add_new(0x00100010, "UN", NAME.encode())  # PatientName, but VR UN
    deidentify_dataset(ds, level=level, salt=SECRET)
    assert 0x00100010 not in ds


@pytest.mark.parametrize("level", LEVELS)
@pytest.mark.parametrize("vr", ["UN", "LO"])
def test_unknown_public_tags_removed(level, vr: str) -> None:
    tag = 0x0018FFF0  # even group (not private), but not a DICOM dictionary element
    assert not dictionary_has_tag(tag), "test needs a tag outside the DICOM dictionary"
    ds = slice_ds()
    ds.add_new(tag, vr, PID.encode() if vr == "UN" else "opaque vendor text")
    deidentify_dataset(ds, level=level, salt=SECRET)
    assert tag not in ds


# -- D: identifying attributes the list missed -----------------------------------------


@pytest.mark.parametrize("level", LEVELS)
def test_additional_identifying_attributes_removed(level) -> None:
    ds = slice_ds()
    ds.PatientTelecomInformation = "tel:+1-555-0100"
    ds.MedicalAlerts = "Fictional allergy alert"
    ds.Allergies = "Fictional allergen"
    ds.CurrentPatientLocation = "Ward 9, Bed 4"
    ds.PatientInstitutionResidence = "Fictional Care Home"
    contact = Dataset()
    contact.PersonAddress = "1 Fictional Way"
    contact.PersonTelephoneNumbers = "555-0199"
    contact.PersonTelecomInformation = "mailto:nobody@example.invalid"
    ds.ContentSequence = Sequence([contact])
    deidentify_dataset(ds, level=level, salt=SECRET)
    for kw in (
        "PatientTelecomInformation",
        "MedicalAlerts",
        "Allergies",
        "CurrentPatientLocation",
        "PatientInstitutionResidence",
    ):
        assert kw not in ds, kw
    item = ds.ContentSequence[0]
    for kw in ("PersonAddress", "PersonTelephoneNumbers", "PersonTelecomInformation"):
        assert kw not in item, kw


# -- E: AE titles ----------------------------------------------------------------------


@pytest.mark.parametrize("level", [MODERATE, STRICT])
def test_ae_titles_removed_at_moderate_and_above(level) -> None:
    ds = slice_ds()
    ds.RetrieveAETitle = "FICT_PACS"
    ds.file_meta.SourceApplicationEntityTitle = "FICT_SCANNER"
    deidentify_dataset(ds, level=level, salt=SECRET)
    assert "RetrieveAETitle" not in ds
    assert "SourceApplicationEntityTitle" not in ds.file_meta


# -- F: identifiers quoted in free text ------------------------------------------------


@pytest.mark.parametrize("level", [BASIC, MODERATE])
def test_original_uid_quoted_in_text_is_blanked(level) -> None:
    ds = slice_ds()
    sop = str(ds.SOPInstanceUID)
    ds.DerivationDescription = f"Derived from instance {sop}"
    deidentify_dataset(ds, level=level, salt=SECRET)
    assert sop not in text_of(ds)
    assert ds.DerivationDescription == ""


def test_dates_quoted_in_text_blanked_at_moderate_only() -> None:
    kept, blanked = slice_ds(), slice_ds()
    for ds in (kept, blanked):
        ds.SeriesDescription = "Follow-up of scan on 20240115"  # == StudyDate
    deidentify_dataset(kept, level=BASIC, salt=SECRET)
    deidentify_dataset(blanked, level=MODERATE, salt=SECRET)
    assert kept.SeriesDescription == "Follow-up of scan on 20240115"  # basic keeps dates
    assert blanked.SeriesDescription == ""


@pytest.mark.parametrize("level", [BASIC, MODERATE])
def test_name_in_lowercase_reordered_text_is_blanked(level) -> None:
    ds = slice_ds()
    ds.ProtocolName = "follow-up for patient, test"
    deidentify_dataset(ds, level=level, salt=SECRET)
    assert ds.ProtocolName == ""


# -- G: converted volumes describe what was (not) done ----------------------------------


def _write_series(root: Path, *, burned_in: str | None = None) -> Path:
    root.mkdir(parents=True)
    for i in range(3):
        ds = _make_slice(
            study_uid="1.2.826.0.1.3680043.8.498.55.1",
            series_uid="1.2.826.0.1.3680043.8.498.55.3",
            index=i,
            z=float(i),
        )
        if burned_in is not None:
            ds.BurnedInAnnotation = burned_in
        save_dicom(ds, root / f"{i}.dcm")
    return root


def _nrrd_meta(path: str) -> dict[str, str]:
    import SimpleITK

    image = SimpleITK.ReadImage(path)
    return {k: image.GetMetaData(k) for k in image.GetMetaDataKeys() if k.startswith("dicomforge")}


@pytest.mark.requires_convert
def test_nrrd_records_header_level_and_unverified_pixels(tmp_path: Path) -> None:
    src = _write_series(tmp_path / "src")
    result = run_pipeline(
        src, tmp_path / "out" / "v", config=PipelineConfig(deidentification_level=STRICT)
    )
    assert result.conversion is not None
    meta = _nrrd_meta(result.conversion.output_path)
    assert meta["dicomforge_header_deidentification"] == "strict"
    assert meta["dicomforge_pixel_data"] == "unverified"
    assert meta["dicomforge_version"]


@pytest.mark.requires_convert
def test_nrrd_marks_flagged_series_processed_by_override(tmp_path: Path) -> None:
    src = _write_series(tmp_path / "src", burned_in="YES")
    result = run_pipeline(
        src, tmp_path / "out" / "v", config=PipelineConfig(burned_in_policy="allow")
    )
    assert result.conversion is not None
    meta = _nrrd_meta(result.conversion.output_path)
    assert meta["dicomforge_pixel_data"] == "flagged-burned-in-risk-allowed"


@pytest.mark.requires_convert
def test_nrrd_marks_no_deidentification(tmp_path: Path) -> None:
    src = _write_series(tmp_path / "src")
    result = run_pipeline(src, tmp_path / "out" / "v", config=PipelineConfig(deidentify=False))
    assert result.conversion is not None
    assert _nrrd_meta(result.conversion.output_path)["dicomforge_header_deidentification"] == "none"
