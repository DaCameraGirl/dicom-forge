<p align="center">
  <img src="docs/readme-banner.svg" alt="DICOM Forge — Enterprise medical-imaging pipeline: ingest, de-identify, QC, and convert DICOM for 3D Slicer and ITK-SNAP." width="720" />
</p>

<p align="center">
  <strong>Enterprise medical-imaging pipeline: ingest, de-identify, QC, and convert DICOM for 3D Slicer and ITK-SNAP.</strong>
</p>

<p align="center">
  <a href="https://dacameragirl.github.io/dicom-forge/"><img src="https://img.shields.io/badge/Live-GitHub%20Pages-33d69f?style=for-the-badge&logo=github&logoColor=white" alt="Live demo" /></a>
  <a href="https://github.com/DaCameraGirl/dicom-forge"><img src="https://img.shields.io/badge/Code-GitHub-58a6ff?style=for-the-badge&logo=github&logoColor=white" alt="Source code" /></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/deploy-GitHub Pages-000000?style=flat-square&logo=github&logoColor=white" alt="deploy-GitHub Pages" />
  <img src="https://img.shields.io/badge/compliance-HIPAA ready-4fd6e0?style=flat-square" alt="compliance-HIPAA ready" />
</p>

### Languages

<p align="center">
  <img src="https://img.shields.io/badge/Python-90%25-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/C++-6%25-00599C?style=flat-square&logo=github&logoColor=white" alt="C++" />
</p>

### Stack

<p align="center">
  <img src="https://img.shields.io/badge/Python-pipeline-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python-pipeline" />
  <img src="https://img.shields.io/badge/ITK-SNAP-export-58a6ff?style=flat-square" alt="ITK-SNAP-export" />
</p>

<p align="center">
  Built by <strong>Angela Hudson</strong> · <a href="https://github.com/DaCameraGirl">DaCameraGirl</a>
</p>
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

**An enterprise-grade medical-imaging pipeline that prepares DICOM for [3D Slicer](https://www.slicer.org/) and [ITK-SNAP](http://www.itksnap.org/).**

`dicom-forge` takes a folder of DICOM, **de-identifies** it (strips patient names and IDs from headers), runs **quality control**, and **converts** it into formats clinical-research viewers load natively — NIfTI (`.nii.gz`), NRRD (`.nrrd`), and Slicer's segmentation format (`.seg.nrrd`). Every run produces a serialisable audit record.

It is the headless core of a two-repo system; its companion, [`slicer-forge`](https://github.com/DaCameraGirl/slicer-forge), wraps it in a 3D Slicer extension GUI.

> 📌 **New here?** Read the [**project showcase**](SHOWCASE.md) for the big picture — the problem, the architecture, who it's for, and the engineering highlights.

---

<p align="center"><img src="docs/readme-divider.svg" width="720" alt="" /></p>
<p align="center"><img src="https://capsule-render.vercel.app/api?type=waving&color=0:070b14,100:12102a&height=50&section=header&text=Why%20this%20exists&fontSize=22&fontColor=e6edf3&animation=twinkling" width="720" alt="Why this exists" /></p>


Real imaging pipelines separate a **testable, headless core** from a **thin GUI**. 3D Slicer itself is built this way: ITK/VTK do the work, the GUI is a shell on top. `dicom-forge` is that core — so the logic is unit-tested in CI **without** needing Slicer installed, and the same code runs from the command line, from Python, or inside Slicer's Python console.

<p align="center"><img src="docs/readme-divider.svg" width="720" alt="" /></p>
<p align="center"><img src="https://capsule-render.vercel.app/api?type=waving&color=0:070b14,100:12102a&height=50&section=header&text=Features&fontSize=22&fontColor=e6edf3&animation=twinkling" width="720" alt="Features" /></p>


- **Ingestion** — recursive DICOM discovery, series grouping, geometry-aware slice ordering (handles oblique acquisitions), rescale-slope/intercept applied (CT in HU).
- **De-identification** — three escalating levels modelled on the DICOM PS3.15 Basic Profile, with deterministic salted-hash pseudonymisation of `PatientID`.
- **Quality control** — slice count, geometry consistency, slice-spacing regularity, and intensity statistics, split into blocking errors vs. non-blocking warnings.
- **Conversion** — geometry-preserving export to NIfTI / NRRD via SimpleITK (the ITK core shared with Slicer & ITK-SNAP).
- **Segmentation** — write Slicer-native `.seg.nrrd` label maps with named, coloured segments.
- **Typed & validated** — Pydantic models everywhere, `py.typed`, strict mypy.
- **Two interfaces** — a Rich CLI (`dicomforge`) and a clean Python API.
- **Native ITK pre-flight** — a companion C++/ITK CLI, [`dicom-probe`](native/dicom-probe/), reads a series through ITK's own GDCM path (the engine under Slicer/ITK-SNAP) and reports the true volume geometry as JSON.

<p align="center"><img src="docs/readme-divider.svg" width="720" alt="" /></p>
<p align="center"><img src="https://capsule-render.vercel.app/api?type=waving&color=0:070b14,100:12102a&height=50&section=header&text=Installation&fontSize=22&fontColor=e6edf3&animation=twinkling" width="720" alt="Installation" /></p>


```bash
pip install dicom-anvil            # core (ingest, de-id, QC)
pip install "dicom-anvil[convert]" # + SimpleITK/pynrrd/nibabel for conversion
```

> **Names:** the package installs as `dicom-anvil` (the PyPI name `dicom-forge` was already taken) and imports as `dicomforge`; the repository stays `dicom-forge`.

> The conversion stack (SimpleITK et al.) is an **optional extra** so the core stays lightweight and CI-friendly. Calling a conversion function without it raises a clear `MissingDependencyError` telling you exactly what to install.

<p align="center"><img src="docs/readme-divider.svg" width="720" alt="" /></p>
<p align="center"><img src="https://capsule-render.vercel.app/api?type=waving&color=0:070b14,100:12102a&height=50&section=header&text=Quick%20start&fontSize=22&fontColor=e6edf3&animation=twinkling" width="720" alt="Quick start" /></p>


### Command line

```bash
# List the series in a folder
dicomforge inspect ./study

# Run QC and print a report
dicomforge qc ./study

# Full pipeline: de-identify -> QC -> convert to Slicer NRRD
dicomforge convert ./study ./out/patient01 --format nrrd --deid-level moderate
```

### Python

```python
from dicomforge import run_pipeline, PipelineConfig, OutputFormat

result = run_pipeline(
    "./study",
    "./out/patient01",
    config=PipelineConfig(output_format=OutputFormat.NRRD),
)
print(result.qc.passed)                 # True / False
print(result.conversion.output_path)    # ./out/patient01.nrrd
print(result.model_dump_json(indent=2)) # full audit record
```

<p align="center"><img src="docs/readme-divider.svg" width="720" alt="" /></p>
<p align="center"><img src="https://capsule-render.vercel.app/api?type=waving&color=0:070b14,100:12102a&height=50&section=header&text=Pipeline%20order%20(and%20why%20it%20matters)&fontSize=22&fontColor=e6edf3&animation=twinkling" width="720" alt="Pipeline order (and why it matters)" /></p>


```
ingest ──> de-identify ──> QC ──> convert
```

De-identification runs **before** conversion, so any file written to disk is already free of direct identifiers. De-id is performed **in memory** — your source DICOM is never modified.

> ⚠️ **De-identification is risk reduction, not a legal guarantee.** Burned-in pixel annotations and private vendor tags can still carry PHI. Always review output before releasing it outside a controlled environment.

<p align="center"><img src="docs/readme-divider.svg" width="720" alt="" /></p>
<p align="center"><img src="https://capsule-render.vercel.app/api?type=waving&color=0:070b14,100:12102a&height=50&section=header&text=Development&fontSize=22&fontColor=e6edf3&animation=twinkling" width="720" alt="Development" /></p>


```bash
python -m venv .venv && . .venv/Scripts/activate   # Windows
pip install -e ".[dev,convert]"
pytest                      # run the suite (synthetic DICOM, no real data needed)
ruff check . && mypy        # lint + type-check
```

<p align="center"><img src="docs/readme-divider.svg" width="720" alt="" /></p>
<p align="center"><img src="https://capsule-render.vercel.app/api?type=waving&color=0:070b14,100:12102a&height=50&section=header&text=License&fontSize=22&fontColor=e6edf3&animation=twinkling" width="720" alt="License" /></p>


[PolyForm Noncommercial License 1.0.0](LICENSE) © Angela Hudson

Noncommercial use — personal, research, educational, and other noncommercial purposes as defined by the license — is free. **Any commercial use requires a separate license from the copyright holder.** See [LICENSE](LICENSE) for the full terms, or open an issue to ask about commercial licensing.