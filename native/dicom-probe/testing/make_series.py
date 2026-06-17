"""Write a small, deterministic synthetic CT series for the dicom-probe test.

Standalone (only pydicom + numpy) so the native C++ CI job does not depend on the
Python package being installed. Mirrors the geometry used by dicom-forge's own
pytest fixtures: a 6-slice, 16x16 CT volume with 0.7 mm in-plane spacing and 1.0
mm slice spacing.

Usage:
    python make_series.py <output-directory>
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian, generate_uid

ROWS, COLS, SLICES = 16, 16, 6
IN_PLANE_SPACING = 0.7
SLICE_SPACING = 1.0


def _make_slice(study_uid: str, series_uid: str, index: int) -> Dataset:
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
    ds.InstanceNumber = index + 1

    ds.Rows = ROWS
    ds.Columns = COLS
    ds.PixelSpacing = [IN_PLANE_SPACING, IN_PLANE_SPACING]
    ds.SliceThickness = SLICE_SPACING
    ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
    ds.ImagePositionPatient = [0.0, 0.0, float(index) * SLICE_SPACING]

    base = np.linspace(0, 2000, ROWS * COLS, dtype=np.int16).reshape(ROWS, COLS)
    arr = (base + index * 10).astype(np.int16)
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 1
    ds.PixelData = arr.tobytes()
    return ds


def main(out_dir: str) -> None:
    series_dir = Path(out_dir)
    series_dir.mkdir(parents=True, exist_ok=True)
    study_uid = generate_uid()
    series_uid = generate_uid()
    for i in range(SLICES):
        ds = _make_slice(study_uid, series_uid, i)
        ds.save_as(series_dir / f"slice_{i:03d}.dcm", enforce_file_format=True)
    print(f"wrote {SLICES} slices to {series_dir}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python make_series.py <output-directory>")
    main(sys.argv[1])
