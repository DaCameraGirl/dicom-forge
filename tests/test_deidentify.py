"""Tests for PHI de-identification across levels."""

from __future__ import annotations

import pytest
from pydicom.dataset import Dataset

from dicomforge.deidentify import deidentify_dataset, pseudonymise
from dicomforge.models import DeidentificationLevel


def test_pseudonymise_deterministic() -> None:
    a = pseudonymise("MRN-0001", salt="proj")
    b = pseudonymise("MRN-0001", salt="proj")
    assert a == b
    assert a.startswith("DF-")


def test_pseudonymise_salt_changes_output() -> None:
    assert pseudonymise("MRN-0001", salt="a") != pseudonymise("MRN-0001", salt="b")


def test_basic_removes_direct_identifiers(single_dataset: Dataset) -> None:
    result = deidentify_dataset(single_dataset, level=DeidentificationLevel.BASIC)
    assert "PatientName" not in single_dataset
    assert "ReferringPhysicianName" not in single_dataset
    assert "InstitutionName" not in single_dataset
    assert "PatientName" in result.removed_tags
    # BASIC keeps dates and device identifiers.
    assert single_dataset.StudyDate == "20240115"
    assert "StationName" in single_dataset


def test_moderate_blanks_dates_and_devices(single_dataset: Dataset) -> None:
    deidentify_dataset(single_dataset, level=DeidentificationLevel.MODERATE)
    assert single_dataset.StudyDate == ""
    assert "StationName" not in single_dataset
    assert "DeviceSerialNumber" not in single_dataset


def test_patient_id_pseudonymised(single_dataset: Dataset) -> None:
    original = single_dataset.PatientID
    result = deidentify_dataset(single_dataset, salt="proj")
    assert single_dataset.PatientID != original
    assert single_dataset.PatientID == result.pseudonymised_patient_id
    assert single_dataset.PatientID.startswith("DF-")


def test_patient_id_can_be_kept(single_dataset: Dataset) -> None:
    deidentify_dataset(single_dataset, pseudonymise_patient_id=False)
    assert single_dataset.PatientID == "MRN-0001"


def test_provenance_markers_set(single_dataset: Dataset) -> None:
    deidentify_dataset(single_dataset, level=DeidentificationLevel.BASIC)
    assert single_dataset.PatientIdentityRemoved == "YES"
    assert "dicom-forge basic" in single_dataset.DeidentificationMethod


def test_strict_preserves_safe_list(single_dataset: Dataset) -> None:
    deidentify_dataset(single_dataset, level=DeidentificationLevel.STRICT)
    # Safe-listed tags survive STRICT blanking.
    assert int(single_dataset.Rows) == 16
    assert single_dataset.Modality == "CT"
    assert "PixelData" in single_dataset


def test_strict_blanks_manufacturer(single_dataset: Dataset) -> None:
    assert single_dataset.Manufacturer == "ForgeSim"
    deidentify_dataset(single_dataset, level=DeidentificationLevel.STRICT)
    assert single_dataset.Manufacturer == ""


@pytest.mark.parametrize("level", list(DeidentificationLevel))
def test_all_levels_remove_patient_name(single_dataset: Dataset, level) -> None:
    deidentify_dataset(single_dataset, level=level)
    assert "PatientName" not in single_dataset
