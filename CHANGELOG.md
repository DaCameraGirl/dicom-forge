# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - not yet released

Security release from the 2026-10-26 de-identification audit. **All 0.1.x users should
upgrade**: 0.1.x pseudonyms are reversible, and UIDs, private tags, accession numbers
and nested identifiers are not de-identified. Slicer Forge requires `>= 0.2.0`.

### Security
- **PatientID pseudonyms are now keyed with a private secret.** Earlier versions hashed
  `"dicom-forge:" + PatientID` with SHA-256. That default salt is public, and neither the
  CLI nor the Slicer extension could change it, so structured MRNs could be recovered by
  enumeration. Pseudonyms now use HMAC-SHA256 with a secret taken from
  `PipelineConfig(pseudonym_secret=...)`, then the `DICOMFORGE_PSEUDONYM_SECRET`
  environment variable, then a random per-session key (with a warning).
  Secrets must be at least 16 characters, the public value is rejected, and the secret
  is never serialised or logged, and validation errors no longer echo rejected values.
- **Audit records and logs no longer carry identifying data.** `PipelineResult` used to
  contain the original Study/Series Instance UIDs, the input folder path (identifying
  when folders are named after patients), and metadata read *before*
  de-identification. Now:
  - the audit record is built from the de-identified data, and `source_path` is always
    `None`
  - Study/Series UIDs are replaced by keyed `2.25.<n>` UIDs under the pseudonymisation
    secret
  - the pipeline, ingest, QC, conversion and segmentation logs no longer contain file
    paths or UIDs
  - volume-assembly errors that flow into `qc.errors` name the slice position, not the
    `SOPInstanceUID`
- **PS3.15-aligned de-identification policy** (documented in
  `docs/deidentification-policy.md`), applied recursively through every sequence at
  every level:
  - every PN element and an expanded list of direct identifiers, identifying sequences,
    order/visit IDs and comment fields are removed
  - **all private tags** are removed
  - `AccessionNumber` and `StudyID` are blanked
  - **every instance UID** (including references and file meta) is replaced with a
    keyed `2.25` UID that stays consistent across a series
  - `PatientID` is pseudonymised wherever it appears
  - remaining free text containing the dataset's own identifiers is blanked

  Moderate now blanks *all* dates/times, not 8 listed tags. Strict also removes
  age/size/weight, blanks sex and AS/UC text, and no longer keeps a raw `PatientID`
  when pseudonymisation is disabled.
- The de-identification audit record now covers the **whole series** (it reflected
  only the last slice), with `instances`, `replaced_uids`, `removed_private_tags` and
  `pseudonymised_patient_ids`.
- **Burned-in annotation policy.** Each series is assessed from metadata before
  de-identification. A series is flagged for `BurnedInAnnotation=YES` or an
  unrecognised value, Secondary Capture/`ConversionType`, modality
  US/SC/OT/XC/ES/GM/SM, colour pixels, or an overlay embedded in pixel bits. Flagged
  series are **rejected by default** (`BurnedInAnnotationError`, CLI exit code 3)
  before anything is written; the error and logs carry reason codes only.
  `burned_in_policy="allow"` / `--allow-burned-in` opts in explicitly.
  `PipelineResult.pixel_privacy` records the assessment; unflagged series are
  `unverified`, never clean. Pixel content itself is still not analysed.
- Release-candidate privacy review (adversarial tests in `tests/test_deid_adversarial.py`):
  - overlay (60xx) and curve (50xx) groups are now removed
  - person names stored with VR UN, and public tags outside the DICOM dictionary,
    are now removed
  - more identifying attributes are removed: telecom, alternative-calendar dates,
    residence and location, medical alerts, allergies, and person contact details at
    any depth
  - AE titles, including file-meta source/sending AE titles, are removed at moderate
    and above
  - original UIDs, and dates at moderate and above, quoted in free text are now
    caught by screening
- **Converted volumes record their provenance**: NRRD headers carry
  `dicomforge_version`, `dicomforge_header_deidentification` and
  `dicomforge_pixel_data` (`unverified`, or `flagged-burned-in-risk-allowed` after the
  override), so output can't pass as verified clean data.
- Provenance: `PatientIdentityRemoved` is now `NO`, because pixel data is never
  verified. `DeidentificationMethod` reads "header de-identified; pixels unverified",
  and `LongitudinalTemporalInformationModified` is set.

### Changed
- **Breaking:** `PipelineConfig.pseudonym_salt` is removed; configs that still set it
  fail with an actionable error. Pseudonyms differ from those produced by 0.1.x.
- **Breaking:** `PipelineResult.metadata.series_instance_uid` / `study_instance_uid`
  and `qc.series_instance_uid` hold replacement UIDs when de-identification is on;
  `metadata.source_path` is always `None`. Log messages no longer include paths or UIDs.
- **Breaking:** de-identified datasets carry replacement UIDs at every level, including
  `basic`. Private tags are always removed. `basic` and `moderate` may blank
  descriptions or station names that contain the patient's own identifiers.
  Converted volumes are unaffected: voxels and geometry are identical at every level.
- **Breaking:** series flagged for burned-in annotation now fail by default, including
  through the Slicer extension, which cannot pass `allow`. `PatientIdentityRemoved` is
  `NO` instead of `YES`. `PipelineResult` has a new required `pixel_privacy` field.
- CLI logs and error messages go to **stderr**; stdout carries only results, so
  `dicomforge convert ...` and `--json` output can be piped as JSON.
- CLI failures print one line on stderr instead of a traceback, with documented exit
  codes: 1 processing error, 2 QC failure, 3 burned-in rejection, 4 configuration
  error. The new `ConfigurationError` (also a `ValueError`) is raised for unsafe
  secrets.
- Ingestion errors no longer echo the input path, and `--series` with an unknown UID
  no longer lists the input's original Series UIDs.
- README examples no longer name outputs after patients, and the README and docs
  describe dicom-forge as a research tool, not a validated anonymization tool.

### Fixed
- `README.md` was saved as UTF-16 and contained CP437 mojibake (`ΓÇö`, `Espa├▒ol`,
  broken flag emoji); it is now UTF-8 with LF line endings, with the original text
  restored.
- Repository-wide `ruff check .` / `ruff format --check .` pass again
  (`scripts/gen-readme-i18n.py` formatted; E501/RUF001 ignored there for translated
  prose). The generator no longer overwrites the hand-maintained `README.md`.
- The test suite runs on the declared minimum `pydicom` 2.4 (fixtures used a
  pydicom 3-only `save_as` argument). Tests needing the `convert` extra are marked
  and skipped cleanly without it.

## [0.1.1] - 2026-06-17

### Added
- **`dicom-probe`** — a native **C++/ITK** companion CLI (`native/dicom-probe/`) that
  reads a series through ITK's GDCM path and reports the true volume geometry as JSON.
  Built and exercised end-to-end in CI against a generated synthetic series.

### Changed
- License metadata now uses a **PEP 639 SPDX expression**
  (`license = "PolyForm-Noncommercial-1.0.0"` with `license-files = ["LICENSE"]`),
  replacing the `license = {file = ...}` form that dumped the full licence text into
  PyPI's *License* field. Produces a clean `License-Expression` tag (Metadata 2.4).

## [0.1.0] - 2026-06-17

### Added
- Initial public release of `dicom-forge`.
- DICOM ingestion with series grouping, geometry-aware slice ordering, and HU rescale.
- Three-level PHI de-identification (basic / moderate / strict) with salted-hash
  pseudonymisation of `PatientID`.
- Quality-control gate: geometry, slice-spacing, and intensity checks.
- Geometry-preserving conversion to NIfTI and NRRD via SimpleITK (optional extra).
- Slicer-native `.seg.nrrd` segmentation writer with named, coloured segments.
- Typer CLI: `inspect`, `qc`, `convert`.
- Full pytest suite using synthetic DICOM (no real patient data).
- GitHub Actions CI: lint (ruff), type-check (mypy), test matrix (3.10–3.12).
- Documentation site (mkdocs-material) at https://dacameragirl.github.io/dicom-forge/.
- PyPI release pipeline via OIDC Trusted Publishing.

### Changed
- Relicensed from Apache-2.0 to **PolyForm Noncommercial 1.0.0**: noncommercial use
  (personal, research, educational) is free; any commercial use requires a separate
  license from the copyright holder.
- Published on PyPI as **`dicom-anvil`** (the name `dicom-forge` was already taken). The
  import package remains `dicomforge` and the source repository stays `dicom-forge`; the
  de-identification provenance label is unchanged.

[Unreleased]: https://github.com/DaCameraGirl/dicom-forge/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/DaCameraGirl/dicom-forge/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/DaCameraGirl/dicom-forge/releases/tag/v0.1.0
