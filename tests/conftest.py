"""Shared fixtures: synthetic DICOM series generation.

We never commit real patient data, so tests build a deterministic synthetic CT
series in a temp directory. The generator writes valid, readable DICOM with the
geometry and (intentionally) some PHI tags, so every pipeline stage can be
exercised end-to-end without external fixtures.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pydicom
import pytest
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian, generate_uid

ROWS, COLS = 16, 16


def _make_slice(
    *,
    study_uid: str,
    series_uid: str,
    index: int,
    z: float,
    rows: int = ROWS,
    cols: int = COLS,
    with_phi: bool = True,
) -> Dataset:
    """Build one valid CT slice dataset with geometry (and optional PHI)."""
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = CTImageStorage
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = Dataset()
    ds.file_meta = file_meta

    ds.SOPClassUID = CTImageStorage
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.StudyInstanceUID = study_uid
    ds.SeriesInstanceUID = series_uid
    ds.Modality = "CT"
    ds.Manufacturer = "ForgeSim"
    ds.InstanceNumber = index + 1

    # Geometry
    ds.Rows = rows
    ds.Columns = cols
    ds.PixelSpacing = [0.7, 0.7]
    ds.SliceThickness = 1.0
    ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
    ds.ImagePositionPatient = [0.0, 0.0, float(z)]
    ds.RescaleSlope = 1
    ds.RescaleIntercept = -1024

    # Pixel data: a deterministic gradient + slice-dependent offset (signed 16-bit).
    base = np.linspace(0, 2000, rows * cols, dtype=np.int16).reshape(rows, cols)
    arr = (base + index * 10).astype(np.int16)
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 1  # signed
    ds.PixelData = arr.tobytes()

    if with_phi:
        ds.PatientName = "DOE^JANE"
        ds.PatientID = "MRN-0001"
        ds.PatientBirthDate = "19700101"
        ds.PatientAddress = "123 Test St"
        ds.ReferringPhysicianName = "SMITH^JOHN"
        ds.InstitutionName = "General Hospital"
        ds.StudyDate = "20240115"
        ds.StudyTime = "120000"
        ds.StationName = "CT-SCANNER-01"
        ds.DeviceSerialNumber = "SN-99999"

    return ds


@pytest.fixture
def synthetic_series(tmp_path: Path) -> Path:
    """Write a 6-slice synthetic CT series to disk; return its directory."""
    study_uid = generate_uid()
    series_uid = generate_uid()
    series_dir = tmp_path / "series"
    series_dir.mkdir()
    for i in range(6):
        ds = _make_slice(study_uid=study_uid, series_uid=series_uid, index=i, z=i * 1.0)
        ds.save_as(series_dir / f"slice_{i:03d}.dcm", enforce_file_format=True)
    return series_dir


@pytest.fixture
def two_series(tmp_path: Path) -> Path:
    """Write a directory containing two distinct series (sizes 6 and 3)."""
    study_uid = generate_uid()
    big, small = generate_uid(), generate_uid()
    root = tmp_path / "study"
    root.mkdir()
    for i in range(6):
        _make_slice(study_uid=study_uid, series_uid=big, index=i, z=i * 1.0).save_as(
            root / f"big_{i:03d}.dcm", enforce_file_format=True
        )
    for i in range(3):
        _make_slice(study_uid=study_uid, series_uid=small, index=i, z=i * 1.0).save_as(
            root / f"small_{i:03d}.dcm", enforce_file_format=True
        )
    return root


@pytest.fixture
def single_dataset() -> Dataset:
    """A single in-memory dataset with PHI, for de-identification unit tests."""
    return _make_slice(study_uid=generate_uid(), series_uid=generate_uid(), index=0, z=0.0)


@pytest.fixture
def read_back():
    """Helper to re-read a saved dataset from disk."""

    def _read(path: Path) -> Dataset:
        return pydicom.dcmread(path)

    return _read
