<p align="center">
  <img src="docs/assets/readme-hero.svg" alt="DICOM Forge — de-identify, QC, convert" width="100%"/>
</p>

# dicom-forge

<p align="center">
  <a href="README.md"><img src="https://img.shields.io/badge/🇺🇸_English-2dd4bf?style=for-the-badge" alt="English"/></a>
    <a href="README.es.md"><img src="https://img.shields.io/badge/🇪🇸_Español-1e293b?style=for-the-badge" alt="Español"/></a>
    <a href="README.fr.md"><img src="https://img.shields.io/badge/🇫🇷_Français-1e293b?style=for-the-badge" alt="Français"/></a>
    <a href="README.de.md"><img src="https://img.shields.io/badge/🇩🇪_Deutsch-1e293b?style=for-the-badge" alt="Deutsch"/></a>
    <a href="README.pt-BR.md"><img src="https://img.shields.io/badge/🇧🇷_Português-1e293b?style=for-the-badge" alt="Português"/></a>
</p>
<p align="center">
  <a href="README.zh-CN.md"><img src="https://img.shields.io/badge/🇨🇳_中文-1e293b?style=for-the-badge" alt="中文"/></a>
    <a href="README.ja.md"><img src="https://img.shields.io/badge/🇯🇵_日本語-1e293b?style=for-the-badge" alt="日本語"/></a>
    <a href="README.ko.md"><img src="https://img.shields.io/badge/🇰🇷_한국어-1e293b?style=for-the-badge" alt="한국어"/></a>
    <a href="README.it.md"><img src="https://img.shields.io/badge/🇮🇹_Italiano-1e293b?style=for-the-badge" alt="Italiano"/></a>
    <a href="README.ar.md"><img src="https://img.shields.io/badge/🇸🇦_العربية-1e293b?style=for-the-badge" alt="العربية"/></a>
</p>

<p align="center">
  <img src="docs/assets/deid-scanner.svg" alt="Animated DICOM de-identification — x-ray scan with patient names redacted from paperwork" width="520"/>
</p>

<p align="center">
  <a href="https://github.com/DaCameraGirl/dicom-forge/actions/workflows/ci.yml"><img src="https://github.com/DaCameraGirl/dicom-forge/actions/workflows/ci.yml/badge.svg" alt="CI"/></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python"/></a>
  <a href="https://dacameragirl.github.io/dicom-forge/"><img src="https://img.shields.io/badge/docs-dacameragirl.github.io-2dd4bf.svg" alt="Docs"/></a>
  <img src="https://img.shields.io/badge/license-PolyForm%20Noncommercial%201.0.0-orange.svg" alt="License"/>
</p>

**A medical-imaging research pipeline that prepares DICOM for [3D Slicer](https://www.slicer.org/) and [ITK-SNAP](http://www.itksnap.org/).**

`dicom-forge` takes a folder of DICOM, refuses series whose metadata signals burned-in pixel text, **de-identifies the headers** (names, IDs, private tags, UIDs), runs **quality control**, and **converts** it into formats clinical-research viewers load natively — NIfTI (`.nii.gz`), NRRD (`.nrrd`), and Slicer's segmentation format (`.seg.nrrd`). Every run produces a serialisable audit record.

It is the headless core of a two-repo system; its companion, [`slicer-forge`](https://github.com/DaCameraGirl/slicer-forge), wraps it in a 3D Slicer extension GUI.

> 📌 **New here?** Read the [**project showcase**](SHOWCASE.md) for the big picture — the problem, the architecture, who it's for, and the engineering highlights.

---

## Why this exists

Real imaging pipelines separate a **testable, headless core** from a **thin GUI**. 3D Slicer itself is built this way: ITK/VTK do the work, the GUI is a shell on top. `dicom-forge` is that core — so the logic is unit-tested in CI **without** needing Slicer installed, and the same code runs from the command line, from Python, or inside Slicer's Python console.

## Features

- **Ingestion** — recursive DICOM discovery, series grouping, geometry-aware slice ordering (handles oblique acquisitions), rescale-slope/intercept applied (CT in HU).
- **Header de-identification** — three levels aligned with a [documented subset](https://github.com/DaCameraGirl/dicom-forge/blob/main/docs/deidentification-policy.md) of the DICOM PS3.15 Basic Profile, applied recursively. It removes names, IDs and private tags, replaces UIDs consistently, and screens free text. `PatientID` and UIDs use keyed HMAC pseudonyms under a private project secret. Series whose metadata signals burned-in pixel text are rejected by default.
- **Quality control** — slice count, geometry consistency, slice-spacing regularity, and intensity statistics, split into blocking errors vs. non-blocking warnings.
- **Conversion** — geometry-preserving export to NIfTI / NRRD via SimpleITK (the ITK core shared with Slicer & ITK-SNAP).
- **Segmentation** — write Slicer-native `.seg.nrrd` label maps with named, coloured segments.
- **Typed & validated** — Pydantic models everywhere, `py.typed`, strict mypy.
- **Two interfaces** — a Rich CLI (`dicomforge`) and a clean Python API.
- **Native ITK pre-flight** — a companion C++/ITK CLI, [`dicom-probe`](native/dicom-probe/), reads a series through ITK's own GDCM path (the engine under Slicer/ITK-SNAP) and reports the true volume geometry as JSON.

## Installation

```bash
pip install dicom-anvil            # core (ingest, de-id, QC)
pip install "dicom-anvil[convert]" # + SimpleITK/pynrrd/nibabel for conversion
```

> **Names:** the package installs as `dicom-anvil` (the PyPI name `dicom-forge` was already taken) and imports as `dicomforge`; the repository stays `dicom-forge`.

> The conversion stack (SimpleITK et al.) is an **optional extra** so the core stays lightweight and CI-friendly. Calling a conversion function without it raises a clear `MissingDependencyError` telling you exactly what to install.

## Quick start

### Command line

```bash
# List the series in a folder
dicomforge inspect ./study

# Run QC and print a report
dicomforge qc ./study

# A private per-project secret keeps pseudonyms stable across runs (never commit it)
export DICOMFORGE_PSEUDONYM_SECRET="<from your secrets manager>"

# Full pipeline: burned-in check -> de-identify -> QC -> convert to Slicer NRRD
dicomforge convert ./study ./out/case01 --format nrrd --deid-level moderate
```

### Python

```python
from dicomforge import run_pipeline, PipelineConfig, OutputFormat

result = run_pipeline(
    "./study",
    "./out/case01",
    config=PipelineConfig(output_format=OutputFormat.NRRD),
)
print(result.qc.passed)  # True / False
print(result.pixel_privacy.status)  # "unverified" (never "clean"): pixels are not analysed
print(result.conversion.output_path)  # ./out/case01.nrrd
print(result.model_dump_json(indent=2))  # full audit record
```

## Pipeline order (and why it matters)

```
ingest ──> burned-in check ──> de-identify ──> QC ──> convert
```

Series flagged for burned-in pixel annotation are rejected before anything is written. Header de-identification runs **in memory** before conversion — your source DICOM is never modified. NRRD/NIfTI outputs carry no DICOM header fields, but their voxels are the source pixels, unchanged.

> ⚠️ **Not a validated anonymization tool.** De-identification is header-only risk reduction. There is no HIPAA, GDPR or other regulatory claim, and no clinical validation. Pixel data is never analysed: burned-in text is caught only when metadata signals it. Free-text screening finds only the record's own identifiers, and some quasi-identifiers (age, sex; dates at `basic`) are kept by design. Read the [de-identification policy](https://github.com/DaCameraGirl/dicom-forge/blob/main/docs/deidentification-policy.md) and review output before it leaves a controlled environment.

## Development

```bash
python -m venv .venv && . .venv/Scripts/activate   # Windows
pip install -e ".[dev,convert]"
pytest                      # run the suite (synthetic DICOM, no real data needed)
ruff check . && mypy        # lint + type-check
```

## License

[PolyForm Noncommercial License 1.0.0](LICENSE) © Angela Hudson

Noncommercial use — personal, research, educational, and other noncommercial purposes as defined by the license — is free. **Any commercial use requires a separate license from the copyright holder.** See [LICENSE](LICENSE) for the full terms, or open an issue to ask about commercial licensing.
