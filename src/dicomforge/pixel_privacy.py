"""Burned-in annotation risk: metadata-based detection and a reject-by-default policy.

dicom-forge never analyses or modifies pixel data, so identifying text burned into
the image (names, IDs, dates on ultrasound or screenshots) is copied unchanged into
the converted volume. This module decides, **from metadata only**, whether a series
is known or suspected to carry such text, so the pipeline can refuse it before
anything is written.

A series is *flagged* when any instance shows a risk signal (reason codes):

``burned_in_annotation_yes``
    BurnedInAnnotation (0028,0301) is ``YES``.
``burned_in_annotation_unrecognised``
    BurnedInAnnotation holds a value other than ``YES``/``NO``.
``secondary_capture``
    A Secondary Capture SOP class, or ConversionType present (scanned or captured).
``high_risk_modality``
    US, SC, OT, XC, ES, GM or SM, where on-image text and labels are routine.
``colour_pixels``
    Not MONOCHROME1/2: typical of screenshots and rendered captures.
``overlay_in_pixel_data``
    An overlay stored in the pixel bits rather than its own OverlayData plane.

Everything else is *unverified*: processed, but never reported as clean. A missing
or ``NO`` BurnedInAnnotation is a source declaration, not verification. Pixel text
in a series without any risk signal is **not detected**; see
``docs/deidentification-policy.md``.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from pydicom.dataset import Dataset

from .models import BurnedInPolicy, PixelPrivacyReport

_HIGH_RISK_MODALITIES = frozenset({"US", "SC", "OT", "XC", "ES", "GM", "SM"})
_MONOCHROME = frozenset({"MONOCHROME1", "MONOCHROME2"})
# Secondary Capture Image Storage and its multi-frame variants (PS3.4 B.5).
_SECONDARY_CAPTURE_ROOT = "1.2.840.10008.5.1.4.1.1.7"
# Repeating overlay groups 6000-601E (PS3.3 C.9.2).
_OVERLAY_GROUPS = range(0x6000, 0x6020, 2)


def _indicator(ds: Dataset) -> str:
    value = ds.get("BurnedInAnnotation")
    if value is None or str(value).strip() == "":
        return "absent"
    text = str(value).strip().upper()
    return text if text in ("YES", "NO") else "other"


def _overlay_in_pixel_data(ds: Dataset) -> bool:
    for group in _OVERLAY_GROUPS:
        if (group, 0x0010) not in ds:  # OverlayRows: no overlay in this group
            continue
        bit_position = ds.get((group, 0x0102))
        if (group, 0x3000) not in ds:  # no separate OverlayData plane
            return True
        if bit_position is not None and bit_position.value not in (0, None):
            return True
    return False


def instance_risk_reasons(ds: Dataset) -> list[str]:
    """Reason codes for one instance; empty when metadata shows no risk signal."""
    reasons: list[str] = []
    indicator = _indicator(ds)
    if indicator == "YES":
        reasons.append("burned_in_annotation_yes")
    elif indicator == "other":
        reasons.append("burned_in_annotation_unrecognised")
    if str(ds.get("SOPClassUID", "")).startswith(_SECONDARY_CAPTURE_ROOT) or (
        "ConversionType" in ds
    ):
        reasons.append("secondary_capture")
    if str(ds.get("Modality", "")).strip().upper() in _HIGH_RISK_MODALITIES:
        reasons.append("high_risk_modality")
    photometric = ds.get("PhotometricInterpretation")
    if photometric is not None and str(photometric).strip().upper() not in _MONOCHROME:
        reasons.append("colour_pixels")
    if _overlay_in_pixel_data(ds):
        reasons.append("overlay_in_pixel_data")
    return reasons


def assess_burned_in_risk(
    datasets: Sequence[Dataset], *, policy: BurnedInPolicy
) -> PixelPrivacyReport:
    """Assess a series from metadata only. Never reads or changes pixel values."""
    per_instance = [instance_risk_reasons(ds) for ds in datasets]
    flagged = sum(1 for reasons in per_instance if reasons)
    indicators = Counter(_indicator(ds) for ds in datasets)
    return PixelPrivacyReport(
        status="flagged" if flagged else "unverified",
        policy=policy,
        instances=len(datasets),
        instances_flagged=flagged,
        reasons=tuple(dict.fromkeys(r for reasons in per_instance for r in reasons)),
        burned_in_annotation={
            k: indicators[k] for k in ("YES", "NO", "absent", "other") if indicators[k]
        },
    )


def rejection_message(report: PixelPrivacyReport) -> str:
    """A user-facing explanation with reason codes and counts only (no PHI)."""
    return (
        f"Series rejected: {report.instances_flagged} of {report.instances} instance(s) "
        f"are known or suspected to contain burned-in annotation "
        f"({', '.join(report.reasons)}). dicom-forge does not de-identify pixel data, "
        "so identifying text in the image would reach the output. Review the images; "
        "only if the pixels are confirmed free of identifiers, re-run with "
        "burned_in_policy='allow' (CLI: --allow-burned-in)."
    )
