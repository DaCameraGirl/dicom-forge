<p align="center">
  <img src="docs/assets/readme-hero.svg" alt="DICOM Forge — de-identify, QC, convert" width="100%"/>
</p>

# dicom-forge

<p align="center">
  <a href="README.md"><img src="https://img.shields.io/badge/🇺🇸_English-1e293b?style=for-the-badge" alt="English"/></a>
    <a href="README.es.md"><img src="https://img.shields.io/badge/🇪🇸_Español-2dd4bf?style=for-the-badge" alt="Español"/></a>
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
  <img src="docs/assets/deid-scanner.svg" alt="Desidentificación DICOM animada — escáner con nombres de paciente tachados en el papeleo" width="520"/>
</p>

<p align="center">
  <a href="https://github.com/DaCameraGirl/dicom-forge/actions/workflows/ci.yml"><img src="https://github.com/DaCameraGirl/dicom-forge/actions/workflows/ci.yml/badge.svg" alt="CI"/></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python"/></a>
  <a href="https://dacameragirl.github.io/dicom-forge/"><img src="https://img.shields.io/badge/docs-dacameragirl.github.io-2dd4bf.svg" alt="Documentación"/></a>
  <img src="https://img.shields.io/badge/license-PolyForm%20Noncommercial%201.0.0-orange.svg" alt="License"/>
</p>

**Pipeline de imágenes médicas de nivel empresarial que prepara DICOM para [3D Slicer](https://www.slicer.org/) e [ITK-SNAP](http://www.itksnap.org/).**

`dicom-forge` toma una carpeta de DICOM, la **desidentifica** (elimina nombres e IDs del paciente en las cabeceras), ejecuta **control de calidad** y **convierte** a formatos que los visores clínicos cargan de forma nativa — NIfTI (`.nii.gz`), NRRD (`.nrrd`) y segmentación de Slicer (`.seg.nrrd`). Cada ejecución genera un registro de auditoría serializable.

Es el núcleo sin interfaz de un sistema de dos repos; su compañero, [`slicer-forge`](https://github.com/DaCameraGirl/slicer-forge), lo envuelve en una extensión GUI de 3D Slicer.

> 📌 **¿Nuevo aquí?** Lee el [**showcase del proyecto**](SHOWCASE.md) — el problema, la arquitectura, el público objetivo y los aspectos técnicos.

---

## Por qué existe

Los pipelines reales separan un **núcleo headless comprobable** de una **GUI delgada**. 3D Slicer funciona así: ITK/VTK hacen el trabajo; la GUI es una capa. `dicom-forge` es ese núcleo — probado en CI **sin** instalar Slicer, y usable desde CLI, Python o la consola de Slicer.

## Funciones

- **Ingesta** — descubrimiento recursivo, agrupación de series, orden geométrico de cortes (adquisiciones oblicuas), rescale-slope/intercept (TC en HU).
- **Desidentificación** — tres niveles según el Perfil Básico DICOM PS3.15, con seudonimización determinista de `PatientID`.
- **Control de calidad** — conteo de cortes, geometría, espaciado e intensidad; errores bloqueantes vs. advertencias.
- **Conversión** — exportación a NIfTI / NRRD vía SimpleITK (núcleo ITK compartido con Slicer e ITK-SNAP).
- **Segmentación** — mapas `.seg.nrrd` nativos de Slicer con segmentos nombrados y coloreados.
- **Tipado y validación** — modelos Pydantic, `py.typed`, mypy estricto.
- **Dos interfaces** — CLI Rich (`dicomforge`) y API Python limpia.
- **Pre-vuelo ITK nativo** — CLI C++/ITK [`dicom-probe`](native/dicom-probe/) reporta geometría del volumen como JSON.

## Instalación

```bash
pip install dicom-anvil            # core (ingest, de-id, QC)
pip install "dicom-anvil[convert]" # + SimpleITK/pynrrd/nibabel for conversion
```

> **Nombres:** el paquete se instala como `dicom-anvil` (PyPI) e importa como `dicomforge`; el repositorio sigue siendo `dicom-forge`.

> La pila de conversión (SimpleITK, etc.) es un **extra opcional** para mantener el núcleo ligero. Sin él, verás un `MissingDependencyError` claro.

## Inicio rápido

### Línea de comandos

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

## Orden del pipeline (y por qué importa)

```
ingest ──> de-identify ──> QC ──> convert
```

La desidentificación corre **antes** de la conversión, así que todo archivo en disco ya está libre de identificadores directos. Se hace **en memoria** — el DICOM fuente nunca se modifica.

> ⚠️ **La desidentificación reduce riesgo, no garantiza cumplimiento legal.** Anotaciones quemadas en píxeles y tags privados pueden conservar PHI. Revise la salida antes de compartirla.

## Desarrollo

```bash
python -m venv .venv && . .venv/Scripts/activate   # Windows
pip install -e ".[dev,convert]"
pytest                      # run the suite (synthetic DICOM, no real data needed)
ruff check . && mypy        # lint + type-check
```

## Licencia

[PolyForm Noncommercial License 1.0.0](LICENSE) © Angela Hudson

Uso no comercial gratuito. **Uso comercial requiere licencia separada.** Ver [LICENSE](LICENSE) o abra un issue.
