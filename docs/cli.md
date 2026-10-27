# CLI reference

All commands accept `-v/--verbose` for debug logging and `--version`.

**Output streams.** Results (tables, JSON) go to **stdout**, while logs, warnings and
errors go to **stderr**. `dicomforge convert ... > record.json` therefore produces valid
JSON. On failure, the error is one line on stderr, with no traceback.

**Exit codes.**

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Processing error (no readable DICOM, unknown series, conversion failure) |
| `2` | QC failure (`qc`, or `convert --fail-on-qc`); Typer also uses 2 for usage errors |
| `3` | `convert` rejected the series for burned-in annotation risk |
| `4` | Configuration error, e.g. an unsafe `DICOMFORGE_PSEUDONYM_SECRET` |

!!! warning "`inspect` and `qc` read the original data"
    They do not de-identify. `inspect` prints original Series UIDs and the input path,
    and `qc` reports the original Series UID. Don't share their output outside the
    environment that holds the source data. Only `convert` de-identifies.

## `dicomforge inspect PATH`

List the DICOM series found under `PATH`. Writes nothing.

- `--json` — emit machine-readable JSON instead of a table.

## `dicomforge qc PATH`

Run quality control on the original data and print findings. Exits `2` if QC fails.

- `--series UID` — select a specific series.
- `--json` — emit the full `QCReport` as JSON.

## `dicomforge convert PATH OUTPUT`

Run the full pipeline (de-identify → QC → convert) and write a volume.

- `-f, --format [nifti|nrrd|seg-nrrd]` — output format (default `nrrd`).
- `--deid-level [basic|moderate|strict]` — de-identification level (default `moderate`).
- `--no-deid` — skip de-identification (unsafe; for already-anonymous data).
- `--allow-burned-in` — process series flagged for burned-in pixel annotation (unsafe:
  pixel data is never de-identified). Without it, flagged series are rejected and the
  command exits with code `3`.
- `--fail-on-qc` — abort the run if QC reports a hard error.
- `--series UID` — select a specific series.

The output extension is added automatically (`.nrrd`, `.nii.gz`, `.seg.nrrd`).

### Pseudonymisation secret

`PatientID` pseudonyms are keyed by the `DICOMFORGE_PSEUDONYM_SECRET` environment
variable. There is deliberately no command-line flag, so the secret never lands in
shell history or process listings.

- **Not set:** each run uses a fresh random key from the operating system's
  cryptographically secure generator, and logs a warning. Pseudonyms can't be
  reversed, but the same patient gets a different pseudonym every run.
- **Set:** the same patient gets the same pseudonym in every run that uses the same
  secret. This is required to link a patient's studies across runs, sites or time.

For reproducible pseudonyms, generate one secret per project
(e.g. `python -c "import secrets; print(secrets.token_hex(32))"`). Store it in a
password manager or secrets vault, never in config files or source control. Share it
only with people allowed to re-link pseudonyms. Anyone holding the secret can test
guesses against pseudonyms; changing it breaks continuity with earlier pseudonyms.
Secrets must be at least 16 characters, and the old public default is rejected.
