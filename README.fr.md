<p align="center">
  <img src="docs/assets/readme-hero.svg" alt="DICOM Forge — de-identify, QC, convert" width="100%"/>
</p>

# dicom-forge

<p align="center">
  <a href="README.md"><img src="https://img.shields.io/badge/🇺🇸_English-1e293b?style=for-the-badge" alt="English"/></a>
    <a href="README.es.md"><img src="https://img.shields.io/badge/🇪🇸_Español-1e293b?style=for-the-badge" alt="Español"/></a>
    <a href="README.fr.md"><img src="https://img.shields.io/badge/🇫🇷_Français-2dd4bf?style=for-the-badge" alt="Français"/></a>
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
  <img src="docs/assets/deid-scanner.svg" alt="Dé-identification DICOM animée — scanner et noms patient barrés sur le dossier" width="520"/>
</p>

<p align="center">
  <a href="https://github.com/DaCameraGirl/dicom-forge/actions/workflows/ci.yml"><img src="https://github.com/DaCameraGirl/dicom-forge/actions/workflows/ci.yml/badge.svg" alt="CI"/></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python"/></a>
  <a href="https://dacameragirl.github.io/dicom-forge/"><img src="https://img.shields.io/badge/docs-dacameragirl.github.io-2dd4bf.svg" alt="Documentation"/></a>
  <img src="https://img.shields.io/badge/license-PolyForm%20Noncommercial%201.0.0-orange.svg" alt="License"/>
</p>

**Pipeline d'imagerie médicale prêt pour la production, préparant le DICOM pour [3D Slicer](https://www.slicer.org/) et [ITK-SNAP](http://www.itksnap.org/).**

`dicom-forge` prend un dossier DICOM, le **dé-identifie** (retire noms et identifiants patient des en-têtes), exécute un **contrôle qualité** et **convertit** vers NIfTI (`.nii.gz`), NRRD (`.nrrd`) et segmentation Slicer (`.seg.nrrd`). Chaque exécution produit un journal d'audit sérialisable.

C'est le cœur headless d'un système à deux dépôts ; le compagnon [`slicer-forge`](https://github.com/DaCameraGirl/slicer-forge) l'enveloppe dans une extension 3D Slicer.

> 📌 **Nouveau ?** Lisez le [**showcase**](SHOWCASE.md) — problème, architecture, public et points techniques.

---

## Pourquoi ce projet

Les vrais pipelines séparent un **noyau headless testable** d'une **GUI fine**. 3D Slicer fonctionne ainsi. `dicom-forge` est ce noyau — testé en CI **sans** Slicer, utilisable en CLI, Python ou console Slicer.

## Fonctionnalités

- **Ingestion** — découverte récursive, regroupement de séries, ordre géométrique des coupes.
- **Dé-identification** — trois niveaux selon le profil DICOM PS3.15, pseudonymisation de `PatientID`.
- **Contrôle qualité** — géométrie, espacement, intensité ; erreurs bloquantes vs avertissements.
- **Conversion** — export NIfTI / NRRD via SimpleITK.
- **Segmentation** — cartes `.seg.nrrd` Slicer.
- **Typé et validé** — Pydantic, `py.typed`, mypy strict.
- **Deux interfaces** — CLI Rich (`dicomforge`) et API Python.
- **Pré-vol ITK** — [`dicom-probe`](native/dicom-probe/) en C++/ITK.

## Installation

```bash
pip install dicom-anvil            # core (ingest, de-id, QC)
pip install "dicom-anvil[convert]" # + SimpleITK/pynrrd/nibabel for conversion
```

> **Noms :** paquet PyPI `dicom-anvil`, import `dicomforge`, dépôt `dicom-forge`.

> SimpleITK est un **extra optionnel** pour un noyau léger.

## Démarrage rapide

### Ligne de commande

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

## Ordre du pipeline

```
ingest ──> de-identify ──> QC ──> convert
```

La dé-identification précède la conversion ; traitement **en mémoire** — la source n'est jamais modifiée.

> ⚠️ **Réduction de risque, pas garantie juridique.** Vérifiez toujours la sortie avant diffusion.

## Développement

```bash
python -m venv .venv && . .venv/Scripts/activate   # Windows
pip install -e ".[dev,convert]"
pytest                      # run the suite (synthetic DICOM, no real data needed)
ruff check . && mypy        # lint + type-check
```

## Licence

[PolyForm Noncommercial License 1.0.0](LICENSE) © Angela Hudson — usage non commercial gratuit ; **licence commerciale séparée requise.**
