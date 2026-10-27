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

Every level applies the core PS3.15-aligned rules **recursively**:

- names (all PN elements) and direct identifiers are removed
- private tags are removed
- AccessionNumber and StudyID are blanked
- instance UIDs are replaced consistently
- PatientID is pseudonymised
- free text containing the dataset's own identifiers is blanked

| Level    | Dates/times   | Device IDs | Age/sex/size/weight | Other free text |
|----------|---------------|------------|---------------------|-----------------|
| basic    | kept          | kept       | kept                | screened        |
| moderate | blanked (all) | removed    | kept                | screened        |
| strict   | blanked (all) | removed    | removed / blanked   | blanked         |

Pixel data is never analysed or modified at any level. Before de-identification, each
series is checked from **metadata** for known or suspected burned-in annotation
(e.g. `BurnedInAnnotation=YES`, ultrasound, secondary capture, colour screenshots).
Flagged series are rejected by default. Unflagged series are reported as `unverified`,
never as clean. The exact rules and limitations are in the
[de-identification policy](deidentification-policy.md).

`PatientID` is replaced with a keyed HMAC-SHA256 pseudonym. The same patient maps to the
same id for as long as the same secret is used. Without the secret, the pseudonym can't be
recomputed or reversed by guessing likely IDs. Set a private secret of at least 16
characters in the `DICOMFORGE_PSEUDONYM_SECRET` environment variable. Keep it out of
config files and source control. If no secret is set, a random key is generated for each
session from a cryptographically secure source: pseudonyms are then safe but not stable
across sessions. **Reproducible pseudonyms across separate runs require a securely
managed, consistent project secret**; see [the CLI reference](cli.md#pseudonymisation-secret).

Rejected secrets are never echoed in error messages or tracebacks. Note that pydantic's
structured `ValidationError.errors()` still returns the caller's own input; code that
logs it should call `errors(include_input=False)`.

## Audit records and logs

The `PipelineResult` audit record is built from the de-identified data, not the source:

- `metadata.source_path` is always `None`; input folder names often identify the patient.
- With de-identification on, `metadata.series_instance_uid`, `metadata.study_instance_uid`
  and `qc.series_instance_uid` are the replacement UIDs (`2.25.<n>`) that the
  de-identified datasets carry, keyed by the pseudonymisation secret. They are stable
  for the same secret, so records from one project still correlate, but they can't be
  traced back to the PACS without the secret. With `--no-deid` the original UIDs are
  kept, since nothing is being de-identified.
- `deidentification` covers every instance in the series (`instances`, unions of
  removed/blanked/replaced elements, a total of removed private tags).
- `conversion.output_path` is the destination **you** chose. It is kept because
  callers, including the Slicer extension, load the volume from it. Don't name output
  folders or files after patients.

Logs never include file paths or UIDs, at any level including DEBUG.

The NRRD/NIfTI output contains no DICOM header fields at all, but pixel data,
including any burned-in annotations, is copied unchanged.
