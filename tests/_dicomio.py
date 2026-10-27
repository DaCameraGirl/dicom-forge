"""Write test DICOM files across the supported pydicom range (>=2.4,<4)."""

from __future__ import annotations

from pathlib import Path

import pydicom
from pydicom.dataset import Dataset

_PYDICOM_3 = int(pydicom.__version__.split(".")[0]) >= 3


def save_dicom(ds: Dataset, path: Path) -> None:
    """Save ``ds`` as a standard DICOM file (preamble + file meta).

    pydicom 3 spells this ``enforce_file_format=True``; pydicom 2 spells it
    ``write_like_original=False``.
    """
    if _PYDICOM_3:
        ds.save_as(path, enforce_file_format=True)
    else:
        ds.is_little_endian, ds.is_implicit_VR = True, False  # match ExplicitVRLittleEndian
        ds.save_as(path, write_like_original=False)
