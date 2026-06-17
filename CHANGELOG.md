# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/DaCameraGirl/dicom-forge/commits/main
