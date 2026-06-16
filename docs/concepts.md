# Concepts

## Pipeline order

```
ingest ──> de-identify ──> QC ──> convert
```

The order is deliberate:

1. **Ingest** — discover DICOM, group by `SeriesInstanceUID`, sort slices along the
   acquisition normal (robust to oblique scans), and apply rescale slope/intercept so
   CT data is in Hounsfield units.
2. **De-identify** — remove/blank PHI **in memory** before anything is written, so no
   artefact on disk carries direct identifiers. Source files are never modified.
3. **QC** — validate geometry and slice spacing and compute intensity statistics, so
   problems surface while the original DICOM is still available to investigate.
4. **Convert** — write a geometry-preserving NIfTI/NRRD that loads into Slicer or
   ITK-SNAP in correct anatomical space.

## Headless core, thin GUI

`dicom-forge` is the **headless core**. The companion `slicer-forge` extension is the
**GUI** that calls into it from inside 3D Slicer. This mirrors how Slicer itself is
built (ITK/VTK do the work; the GUI is a shell) and means the heavy logic is unit
tested in CI without needing Slicer installed.

## Optional native dependencies

Ingestion, de-identification, and QC need only `pydicom` + `numpy`. Conversion needs
SimpleITK/pynrrd/nibabel, which are installed via the `convert` extra. Calling a
conversion function without the extra raises a clear `MissingDependencyError`.

## De-identification levels

| Level    | Removes direct identifiers | Blanks dates/devices | Blanks everything off the safe-list |
|----------|:--------------------------:|:--------------------:|:-----------------------------------:|
| basic    | ✅                         | ❌                   | ❌                                  |
| moderate | ✅                         | ✅                   | ❌                                  |
| strict   | ✅                         | ✅                   | ✅                                  |

`PatientID` is replaced with a deterministic, salted SHA-256 pseudonym, so the same
patient maps to the same id within a project but cannot be reversed.
