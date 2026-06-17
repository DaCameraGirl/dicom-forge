# dicom-probe (native C++/ITK)

A small, fast **pre-flight inspector** for DICOM series, written in C++ against
[ITK](https://itk.org/) — the same imaging toolkit that powers 3D Slicer and
ITK-SNAP.

`dicom-probe` reads a DICOM directory through ITK's GDCM-backed series reader and
prints the **true volume geometry ITK computes** — dimensions, voxel spacing,
origin, and direction cosines — together with intensity statistics, as a single
line of JSON.

## Why it exists alongside the Python engine

`dicom-forge`'s Python [`qc`](../../src/dicomforge/qc.py) module inspects DICOM
*tags* slice-by-slice. `dicom-probe` is the complement: it validates the
**authoritative ITK load path** and reports the geometry a downstream ITK/Slicer
pipeline will actually see. Use it as a fast native answer to *"will this series
load cleanly as a coherent volume, and as what?"* before committing to a full run
— with no Python or SimpleITK needed.

## Build

Requires a C++17 compiler, CMake ≥ 3.16, and ITK 5 with the GDCM IO module.

```bash
# Debian/Ubuntu: sudo apt-get install cmake g++ libinsighttoolkit5-dev
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
```

## Use

```bash
./build/dicom-probe /path/to/dicom/dir
```

```json
{"ok":true,"directory":"/path/to/dicom/dir","series_instance_uid":"1.2.840...",
 "series_found":1,"slices":6,"dimensions":[16,16,6],"spacing":[0.7,0.7,1],
 "origin":[0,0,0],"direction":[1,0,0,0,1,0,0,0,1],
 "intensity":{"min":0,"max":2050,"mean":1004.2}}
```

If a directory holds several series, the largest (most slices) is probed; pass
`--series <SeriesInstanceUID>` to select a specific one.

Exit codes: `0` success · `1` usage · `2` no series found · `3` requested series
absent · `4` ITK could not read the series. A JSON object with `"ok": false` and
an `"error"` message is printed on failure too, so stdout always parses.

## Tested in CI

The `Native ITK CLI (C++)` job in [`ci.yml`](../../.github/workflows/ci.yml)
builds this tool, generates a synthetic DICOM series with
[`testing/make_series.py`](testing/make_series.py), runs `dicom-probe` on it, and
asserts the reported geometry with
[`testing/check_probe.py`](testing/check_probe.py) — a real cross-language
end-to-end check.
