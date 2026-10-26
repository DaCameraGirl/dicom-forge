"""Regression tests for the burned-in annotation policy (audit finding V15).

The pipeline copies pixel data unchanged and never analyses it, so burned-in text
reaches the converted volume. Series whose metadata indicates known or suspected
burned-in annotation must be rejected before anything is written. A missing or
``NO`` indicator is never treated as proof of clean pixels.

Pixel text is drawn with a tiny built-in bitmap font. Every value is fictional.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pydicom
import pytest
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import (
    CTImageStorage,
    ExplicitVRLittleEndian,
    MRImageStorage,
    SecondaryCaptureImageStorage,
)

from _dicomio import save_dicom
from dicomforge.config import PipelineConfig
from dicomforge.deidentify import deidentify_dataset
from dicomforge.exceptions import BurnedInAnnotationError, DeidentificationError
from dicomforge.pipeline import run_pipeline
from dicomforge.pixel_privacy import assess_burned_in_risk

ENV = "DICOMFORGE_PSEUDONYM_SECRET"
SECRET = "burned-in-test-secret-0123456789ab"
ROOT = "1.2.826.0.1.3680043.8.498.66"
NAME, PID = "TEST^PATIENT", "TEST-12345"
IDENTIFYING_DIR = "TEST_PATIENT_TEST-12345"
SIZE = 64
TEXT_VALUE = 3000
BACKGROUND = 100

# 5x7 bitmap glyphs, just enough for the fictional identifiers.
_GLYPHS = {
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "E": ["11111", "10000", "11110", "10000", "10000", "10000", "11111"],
    "S": ["01111", "10000", "01110", "00001", "00001", "10001", "01110"],
    "P": ["11110", "10001", "11110", "10000", "10000", "10000", "10000"],
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00010", "00100", "01000", "10000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["10010", "10010", "10010", "11111", "00010", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    " ": ["00000"] * 7,
}


def draw_text(img: np.ndarray, text: str, row: int, col: int) -> None:
    for ch in text:
        for r, line in enumerate(_GLYPHS[ch]):
            for c, bit in enumerate(line):
                if bit == "1":
                    img[row + r, col + c] = TEXT_VALUE
        col += 6


def text_image(index: int, with_text: bool = True) -> np.ndarray:
    img = np.full((SIZE, SIZE), BACKGROUND, dtype=np.int16)
    img[20:44, 20:44] = 800 + index  # "anatomy"
    if with_text:  # 6 px per glyph: keep each line within the 64 px width
        draw_text(img, "TEST", 2, 1)
        draw_text(img, "PATIENT", 11, 1)
        draw_text(img, "TEST-12345", 54, 1)
    return img


def make_slice(
    i: int,
    *,
    series: str,
    modality: str = "MR",
    sop_class: str = MRImageStorage,
    burned_in: str | None = None,
    with_text: bool = True,
) -> Dataset:
    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = sop_class
    meta.MediaStorageSOPInstanceUID = f"{ROOT}.{series}.{i + 1}"
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds = Dataset()
    ds.file_meta = meta
    ds.SOPClassUID = sop_class
    ds.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
    ds.StudyInstanceUID = f"{ROOT}.1"
    ds.SeriesInstanceUID = f"{ROOT}.{series}"
    ds.Modality = modality
    ds.PatientName = NAME
    ds.PatientID = PID
    if burned_in is not None:
        ds.BurnedInAnnotation = burned_in
    ds.InstanceNumber = i + 1
    ds.Rows = ds.Columns = SIZE
    ds.PixelSpacing = [0.5, 0.5]
    ds.SliceThickness = 2.0
    ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
    ds.ImagePositionPatient = [0.0, 0.0, i * 2.0]
    ds.RescaleSlope, ds.RescaleIntercept = 1, 0
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.BitsAllocated = ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 1
    ds.PixelData = text_image(i, with_text).tobytes()
    return ds


def write_series(root: Path, n: int = 4, **kw) -> Path:
    root.mkdir(parents=True)
    series = kw.pop("series", "2")
    for i in range(n):
        save_dicom(make_slice(i, series=series, **kw), root / f"s{i}.dcm")
    return root


def hashes(d: Path) -> dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in d.iterdir()}


def leaks(text: str, root: Path) -> list[str]:
    uids = {
        str(v)
        for p in root.glob("*.dcm")
        for v in (pydicom.dcmread(p).SOPInstanceUID, pydicom.dcmread(p).SeriesInstanceUID)
    }
    needles = [IDENTIFYING_DIR, str(root), NAME, PID, *uids]
    return [n for n in needles if n in text]


class _Capture(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.DEBUG)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


@pytest.fixture
def logs() -> Iterator[_Capture]:
    logger = logging.getLogger("dicomforge")
    handler, old = _Capture(), logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    yield handler
    logger.removeHandler(handler)
    logger.setLevel(old)


@pytest.fixture(autouse=True)
def _secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV, SECRET)


# -- assessment (metadata only) ------------------------------------------------


def _ds(**kw) -> Dataset:
    return make_slice(0, series="9", **kw)


@pytest.mark.parametrize(
    ("kwargs", "reason"),
    [
        ({"burned_in": "YES"}, "burned_in_annotation_yes"),
        ({"burned_in": "UNKNOWN"}, "burned_in_annotation_unrecognised"),
        ({"modality": "US"}, "high_risk_modality"),
        ({"modality": "OT"}, "high_risk_modality"),
        ({"modality": "XC"}, "high_risk_modality"),
        ({"sop_class": SecondaryCaptureImageStorage}, "secondary_capture"),
    ],
)
def test_risk_signals_flag_the_series(kwargs: dict, reason: str) -> None:
    report = assess_burned_in_risk([_ds(**kwargs)], policy="reject")
    assert report.status == "flagged"
    assert reason in report.reasons
    assert report.instances_flagged == 1


def test_conversion_type_flags() -> None:
    ds = _ds()
    ds.ConversionType = "WSD"
    assert "secondary_capture" in assess_burned_in_risk([ds], policy="reject").reasons


def test_colour_pixels_flag() -> None:
    ds = _ds()
    ds.PhotometricInterpretation = "RGB"
    ds.SamplesPerPixel = 3
    assert "colour_pixels" in assess_burned_in_risk([ds], policy="reject").reasons


def test_overlay_embedded_in_pixel_data_flags() -> None:
    ds = _ds()
    ds.add_new(0x60000010, "US", SIZE)  # OverlayRows
    ds.add_new(0x60000102, "US", 15)  # OverlayBitPosition: embedded in pixel bits
    assert "overlay_in_pixel_data" in assess_burned_in_risk([ds], policy="reject").reasons


@pytest.mark.parametrize("indicator", [None, "NO"])
def test_missing_or_no_indicator_is_unverified_not_clean(indicator: str | None) -> None:
    report = assess_burned_in_risk([_ds(burned_in=indicator)], policy="reject")
    assert report.status == "unverified"
    assert report.pixel_content_verified is False
    assert report.pixels_modified is False


def test_indicator_counts_recorded() -> None:
    datasets = [_ds(burned_in="NO"), _ds(burned_in="NO"), _ds(), _ds(burned_in="YES")]
    report = assess_burned_in_risk(datasets, policy="reject")
    assert report.burned_in_annotation == {"YES": 1, "NO": 2, "absent": 1}
    assert report.instances == 4 and report.instances_flagged == 1


def test_error_class_is_a_deidentification_error() -> None:
    assert issubclass(BurnedInAnnotationError, DeidentificationError)


@pytest.mark.requires_convert
def test_rejection_carries_structured_report(tmp_path: Path) -> None:
    """Callers such as the Slicer extension need reason codes, not message parsing."""
    root = write_series(tmp_path / "src", modality="US")
    with pytest.raises(BurnedInAnnotationError) as excinfo:
        run_pipeline(root, tmp_path / "out" / "vol")
    report = excinfo.value.report
    assert report is not None
    assert report.status == "flagged" and report.reasons == ("high_risk_modality",)
    assert report.instances == report.instances_flagged == 4


# -- provenance attributes ---------------------------------------------------------


@pytest.mark.parametrize("indicator", [None, "NO", "YES"])
def test_patient_identity_removed_never_claims_pixels(indicator: str | None) -> None:
    ds = _ds(burned_in=indicator)
    deidentify_dataset(ds, salt=SECRET)
    # Pixel data is never verified, so the identity cannot be declared fully removed.
    assert ds.PatientIdentityRemoved == "NO"
    assert "pixels unverified" in ds.DeidentificationMethod
    assert len(ds.DeidentificationMethod) <= 64  # LO
    if indicator is not None:
        assert ds.BurnedInAnnotation == indicator  # source declaration left as-is


# -- pipeline: rejection -----------------------------------------------------------


@pytest.fixture
def flagged_study(tmp_path: Path) -> Path:
    """Burned-in text in the pixels, declared via BurnedInAnnotation=YES."""
    return write_series(tmp_path / "inbox" / IDENTIFYING_DIR, burned_in="YES")


@pytest.mark.requires_convert
def test_flagged_series_rejected_before_any_write(flagged_study: Path, tmp_path: Path) -> None:
    before = hashes(flagged_study)
    out = tmp_path / "out"
    with pytest.raises(BurnedInAnnotationError):
        run_pipeline(flagged_study, out / "vol")
    assert not out.exists() or not any(out.rglob("*"))
    assert hashes(flagged_study) == before


@pytest.mark.requires_convert
@pytest.mark.parametrize("level", ["basic", "moderate", "strict"])
def test_rejection_applies_at_every_level(flagged_study: Path, tmp_path: Path, level: str) -> None:
    with pytest.raises(BurnedInAnnotationError):
        run_pipeline(
            flagged_study,
            tmp_path / "out" / "vol",
            config=PipelineConfig(deidentification_level=level),
        )


@pytest.mark.requires_convert
def test_rejection_applies_without_deidentification(flagged_study: Path, tmp_path: Path) -> None:
    with pytest.raises(BurnedInAnnotationError):
        run_pipeline(
            flagged_study, tmp_path / "out" / "vol", config=PipelineConfig(deidentify=False)
        )


@pytest.mark.requires_convert
def test_one_flagged_slice_rejects_the_series(tmp_path: Path) -> None:
    root = write_series(tmp_path / "mixed", burned_in="NO")
    save_dicom(make_slice(1, series="2", burned_in="YES"), root / "s1.dcm")
    with pytest.raises(BurnedInAnnotationError, match="1 of 4"):
        run_pipeline(root, tmp_path / "out" / "vol")


@pytest.mark.requires_convert
def test_rejection_message_and_logs_are_safe(
    flagged_study: Path, tmp_path: Path, logs: _Capture
) -> None:
    with pytest.raises(BurnedInAnnotationError) as excinfo:
        run_pipeline(flagged_study, tmp_path / "out" / "vol")
    message = str(excinfo.value)
    assert "burned_in_annotation_yes" in message
    assert "allow" in message  # says how to override, explicitly
    assert leaks(message, flagged_study) == []
    assert leaks("\n".join(logs.messages), flagged_study) == []


@pytest.mark.parametrize(
    "kwargs",
    [{"modality": "US"}, {"sop_class": SecondaryCaptureImageStorage, "modality": "OT"}],
    ids=["ultrasound", "secondary-capture"],
)
@pytest.mark.requires_convert
def test_high_risk_sources_rejected_without_indicator(tmp_path: Path, kwargs: dict) -> None:
    root = write_series(tmp_path / "src", **kwargs)
    with pytest.raises(BurnedInAnnotationError):
        run_pipeline(root, tmp_path / "out" / "vol")


# -- pipeline: explicit override ---------------------------------------------------


@pytest.mark.requires_convert
def test_allow_policy_processes_and_records_the_risk(
    flagged_study: Path, tmp_path: Path, logs: _Capture
) -> None:
    result = run_pipeline(
        flagged_study, tmp_path / "out" / "vol", config=PipelineConfig(burned_in_policy="allow")
    )
    report = result.pixel_privacy
    assert report.status == "flagged" and report.policy == "allow"
    assert report.pixel_content_verified is False
    assert any("burned-in" in m.lower() for m in logs.messages)
    assert leaks("\n".join(logs.messages), flagged_study) == []
    assert result.conversion is not None


def test_config_rejects_unknown_policy() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError) as excinfo:
        PipelineConfig(burned_in_policy="ignore")
    assert excinfo.value.errors()[0]["type"] == "literal_error"  # known field, bad value
    assert PipelineConfig().burned_in_policy == "reject"  # safe default


# -- pipeline: unflagged series still work, but are never called clean ------------


@pytest.mark.requires_convert
def test_safe_series_completes_normal_workflow(synthetic_series: Path, tmp_path: Path) -> None:
    import SimpleITK as sitk

    before = hashes(synthetic_series)
    result = run_pipeline(synthetic_series, tmp_path / "out" / "vol")
    assert result.qc.passed
    assert result.conversion is not None
    image = sitk.ReadImage(result.conversion.output_path)
    assert image.GetSize() == (16, 16, 6)
    assert image.GetSpacing() == pytest.approx((0.7, 0.7, 1.0))
    assert result.pixel_privacy.status == "unverified"
    assert result.pixel_privacy.pixel_content_verified is False
    assert hashes(synthetic_series) == before


@pytest.mark.requires_convert
def test_limitation_unflagged_burned_in_text_is_not_detected(tmp_path: Path) -> None:
    """Documented limitation: pixels are not analysed.

    An MR series with fictional text burned into the pixels but *no* metadata signal is
    processed, and the text reaches the output volume. The report says "unverified",
    never "clean". If pixel analysis is ever added, this test should be revisited.
    """
    import SimpleITK as sitk

    root = write_series(tmp_path / "src", burned_in="NO")  # declared NO, but has text
    result = run_pipeline(root, tmp_path / "out" / "vol")
    assert result.pixel_privacy.status == "unverified"
    assert result.conversion is not None
    volume = sitk.GetArrayFromImage(sitk.ReadImage(result.conversion.output_path))
    assert (volume == TEXT_VALUE).any()  # the burned-in text survived


@pytest.mark.requires_convert
def test_audit_record_keeps_slicer_contract(synthetic_series: Path, tmp_path: Path) -> None:
    record = run_pipeline(synthetic_series, tmp_path / "out" / "vol").model_dump(mode="json")
    assert record["metadata"]["modality"] == "CT"
    assert record["qc"]["errors"] == []
    assert Path(record["conversion"]["output_path"]).exists()
    assert record["pixel_privacy"]["status"] == "unverified"


# -- CLI ---------------------------------------------------------------------------


@pytest.mark.requires_convert
def test_cli_rejects_with_safe_message(flagged_study: Path, tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from dicomforge.cli import app

    result = CliRunner().invoke(
        app, ["convert", str(flagged_study), str(tmp_path / "out" / "vol")], env={ENV: SECRET}
    )
    assert result.exit_code == 3, result.output
    assert "burned-in" in result.output.lower()
    assert leaks(result.output, flagged_study) == []


@pytest.mark.requires_convert
def test_cli_allow_flag_overrides(flagged_study: Path, tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from dicomforge.cli import app

    result = CliRunner().invoke(
        app,
        ["convert", str(flagged_study), str(tmp_path / "out" / "vol"), "--allow-burned-in"],
        env={ENV: SECRET},
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "out" / "vol.nrrd").exists()


# -- CT geometry unaffected -----------------------------------------------------------


@pytest.mark.requires_convert
def test_ct_geometry_unchanged_by_assessment(tmp_path: Path) -> None:
    import SimpleITK as sitk

    root = write_series(tmp_path / "ct", modality="CT", sop_class=CTImageStorage, with_text=False)
    plain = run_pipeline(root, tmp_path / "a" / "v", config=PipelineConfig(deidentify=False))
    deid = run_pipeline(root, tmp_path / "b" / "v")
    assert plain.conversion is not None and deid.conversion is not None
    a = sitk.ReadImage(plain.conversion.output_path)
    b = sitk.ReadImage(deid.conversion.output_path)
    assert np.array_equal(sitk.GetArrayFromImage(a), sitk.GetArrayFromImage(b))
    assert (a.GetSpacing(), a.GetOrigin(), a.GetDirection()) == (
        b.GetSpacing(),
        b.GetOrigin(),
        b.GetDirection(),
    )
