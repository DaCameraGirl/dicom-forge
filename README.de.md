<p align="center">
  <img src="docs/assets/readme-hero.svg" alt="DICOM Forge — de-identify, QC, convert" width="100%"/>
</p>

# dicom-forge

<p align="center">
  <a href="README.md"><img src="https://img.shields.io/badge/🇺🇸_English-1e293b?style=for-the-badge" alt="English"/></a>
    <a href="README.es.md"><img src="https://img.shields.io/badge/🇪🇸_Español-1e293b?style=for-the-badge" alt="Español"/></a>
    <a href="README.fr.md"><img src="https://img.shields.io/badge/🇫🇷_Français-1e293b?style=for-the-badge" alt="Français"/></a>
    <a href="README.de.md"><img src="https://img.shields.io/badge/🇩🇪_Deutsch-2dd4bf?style=for-the-badge" alt="Deutsch"/></a>
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
  <img src="docs/assets/deid-scanner.svg" alt="Animierte DICOM-De-Identifizierung — Röntgen und geschwärzte Patientennamen" width="520"/>
</p>

<p align="center">
  <a href="https://github.com/DaCameraGirl/dicom-forge/actions/workflows/ci.yml"><img src="https://github.com/DaCameraGirl/dicom-forge/actions/workflows/ci.yml/badge.svg" alt="CI"/></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python"/></a>
  <a href="https://dacameragirl.github.io/dicom-forge/"><img src="https://img.shields.io/badge/docs-dacameragirl.github.io-2dd4bf.svg" alt="Dokumentation"/></a>
  <img src="https://img.shields.io/badge/license-PolyForm%20Noncommercial%201.0.0-orange.svg" alt="License"/>
</p>

**Enterprise-Pipeline für medizinische Bildgebung — bereitet DICOM für [3D Slicer](https://www.slicer.org/) und [ITK-SNAP](http://www.itksnap.org/) vor.**

`dicom-forge` nimmt einen DICOM-Ordner, **de-identifiziert** ihn (entfernt Patientennamen und IDs aus Headern), führt **Qualitätskontrolle** durch und **konvertiert** nach NIfTI, NRRD und Slicer-Segmentierung. Jeder Lauf erzeugt einen serialisierbaren Audit-Datensatz.

Headless-Kern eines Zwei-Repo-Systems; [`slicer-forge`](https://github.com/DaCameraGirl/slicer-forge) ist die 3D-Slicer-GUI.

> 📌 **Neu hier?** [**Showcase**](SHOWCASE.md) lesen — Problem, Architektur, Zielgruppe.

---

## Warum es existiert

Echte Pipelines trennen **testbaren Headless-Kern** und **dünne GUI**. `dicom-forge` ist dieser Kern — CI ohne Slicer, nutzbar per CLI, Python oder Slicer-Konsole.

## Funktionen

- **Ingestion**, **De-Identifizierung** (3 Stufen, DICOM PS3.15), **QC**, **Konvertierung**, **Segmentierung**
- Pydantic, mypy, Rich-CLI (`dicomforge`), Python-API, [`dicom-probe`](native/dicom-probe/)

## Installation

```bash
pip install dicom-anvil            # core (ingest, de-id, QC)
pip install "dicom-anvil[convert]" # + SimpleITK/pynrrd/nibabel for conversion
```

> PyPI-Name: `dicom-anvil`, Import: `dicomforge`.

> SimpleITK ist ein **optionales Extra**.

## Schnellstart

### Kommandozeile

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

## Pipeline-Reihenfolge

```
ingest ──> de-identify ──> QC ──> convert
```

De-ID **vor** Konvertierung, **im Speicher** — Quell-DICOM unverändert.

> ⚠️ **Risikoreduktion, keine Rechtsgarantie.** Ausgabe vor Freigabe prüfen.

## Entwicklung

```bash
python -m venv .venv && . .venv/Scripts/activate   # Windows
pip install -e ".[dev,convert]"
pytest                      # run the suite (synthetic DICOM, no real data needed)
ruff check . && mypy        # lint + type-check
```

## Lizenz

[PolyForm Noncommercial License 1.0.0](LICENSE) © Angela Hudson — nichtkommerziell frei; **kommerziell separate Lizenz.**
