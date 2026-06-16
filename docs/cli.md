# CLI reference

All commands accept `-v/--verbose` for debug logging and `--version`.

## `dicomforge inspect PATH`

List the DICOM series found under `PATH`. Writes nothing.

- `--json` — emit machine-readable JSON instead of a table.

## `dicomforge qc PATH`

Run quality control and print findings. Exits non-zero (`2`) if QC fails.

- `--series UID` — select a specific series.
- `--json` — emit the full `QCReport` as JSON.

## `dicomforge convert PATH OUTPUT`

Run the full pipeline (de-identify → QC → convert) and write a volume.

- `-f, --format [nifti|nrrd|seg-nrrd]` — output format (default `nrrd`).
- `--deid-level [basic|moderate|strict]` — de-identification level (default `moderate`).
- `--no-deid` — skip de-identification (unsafe; for already-anonymous data).
- `--fail-on-qc` — abort the run if QC reports a hard error.
- `--series UID` — select a specific series.

The output extension is added automatically (`.nrrd`, `.nii.gz`, `.seg.nrrd`).
