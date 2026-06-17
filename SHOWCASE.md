# DICOM Forge — project showcase

> Turning messy, identifiable clinical scans into clean, de-identified,
> quality-checked 3D images that research software can actually use — from the
> command line **or** with one click inside 3D Slicer.

[![CI](https://github.com/DaCameraGirl/dicom-forge/actions/workflows/ci.yml/badge.svg)](https://github.com/DaCameraGirl/dicom-forge/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/dicom-anvil.svg)](https://pypi.org/project/dicom-anvil/)
[![Docs](https://img.shields.io/badge/docs-dacameragirl.github.io-blue.svg)](https://dacameragirl.github.io/dicom-forge/)
[![Languages](https://img.shields.io/badge/built%20with-Python%20·%20C%2B%2B%2FITK%20·%20CMake-informational.svg)](#engineering-highlights)

---

## The problem

Medical scanners (CT, MRI) export images as **DICOM** — and raw DICOM is hostile
to research:

- a single scan is split across **hundreds of separate slice-files**,
- every file is stuffed with **patient identifiers** (name, MRN, birth date…),
- and research/AI tooling can't read it directly — it needs **NIfTI** or **NRRD**.

So before any study, lab, or model can touch the data, someone has to assemble
the slices, strip the identifiers, sanity-check the geometry, and convert the
format. In practice this is done with **fragile, one-off scripts** that no one
trusts and no one documents.

## The solution

**DICOM Forge** is a two-part system that does that pipeline properly — tested,
repeatable, and with an audit trail.

```
        ┌──────────────────────────────────────────────────────────┐
        │                    A folder of raw DICOM                  │
        └──────────────────────────────┬───────────────────────────┘
                                        │
        ╔═══════════════════════════════▼══════════════════════════╗
        ║   dicom-forge  ·  the headless engine  (Python)          ║
        ║                                                          ║
        ║   ingest  →  de-identify  →  quality-control  →  convert ║
        ║   (build    (remove PHI,    (missing slices,   (NIfTI /  ║
        ║    volumes)  3 levels)       bad geometry)      NRRD)    ║
        ║                                                          ║
        ║   …plus a serialisable audit record for every run.       ║
        ╚═══════════════════════════════╦══════════════════════════╝
                                        │
              ┌─────────────────────────┴───────────────────────┐
              ▼                                                  ▼
   ┌────────────────────────┐                     ┌──────────────────────────┐
   │  CLI / Python API      │                     │  slicer-forge             │
   │  (scriptable, headless)│                     │  one-click 3D Slicer GUI  │
   └────────────────────────┘                     └──────────────────────────┘
```

### `dicom-forge` — the engine
The brain of the system, published on PyPI as
[`dicom-anvil`](https://pypi.org/project/dicom-anvil/). A four-stage pipeline:

| Stage | What it does |
|---|---|
| **Ingest** | Discovers scattered slices, groups them into series, orders them by real-world geometry (handles oblique acquisitions), applies CT rescale to Hounsfield units. |
| **De-identify** | Removes protected health information at three escalating levels, with deterministic salted-hash pseudonymisation of patient IDs. |
| **Quality control** | Flags missing slices, irregular spacing, inconsistent geometry, and reports intensity statistics — *before* you rely on the scan. |
| **Convert** | Geometry-preserving export to NIfTI / NRRD (and Slicer-native segmentations). |

Usable as a **command-line tool** or a **typed Python library**.

### `slicer-forge` — the one-click front-end
A [3D Slicer](https://www.slicer.org) extension that puts the whole engine behind
a single **"DICOM Forge Batch"** button: pick a folder, click go, and cleaned-up
volumes load straight into the viewer — batch, cancellable, with progress. No
command line required.

### `dicom-probe` — a native pre-flight inspector
A small, fast **C++/ITK** tool that reads a scan through ITK's own pipeline (the
engine inside Slicer and ITK-SNAP) and reports the *true* volume geometry — a
quick "will this load correctly, and as what?" check.

---

## Who it's for

- **Imaging-research labs & universities** — the core user: turn piles of
  incoming clinical DICOM into shareable, de-identified, analysis-ready volumes,
  in batch, with documentation.
- **Radiologists & clinician-researchers** — who work in 3D Slicer and want a
  one-click import instead of wrestling the command line.
- **Clinical trials & multi-site studies** — where consistent de-identification
  and a documented, repeatable process are compliance requirements, not niceties.
- **AI / ML medical-imaging teams** — who need large batches cleaned and
  converted to NIfTI/NRRD to feed training pipelines.
- **Commercial imaging products** — which can license the engine (see below).

---

## Engineering highlights

What makes this more than a script:

- **Open-core architecture.** All the real logic lives in a **headless,
  independently-tested engine**; the Slicer GUI is a thin shell on top — the same
  separation 3D Slicer itself uses (ITK/VTK do the work, the GUI sits above). The
  engine is unit-tested in CI **without** needing Slicer installed.
- **Genuinely multi-language, and all of it tested.** Python core + a real
  **C++/ITK** companion tool + CMake build. The C++ tool is compiled and run
  against generated DICOM **in CI** — a true cross-language end-to-end test.
- **Tested in a *real* headless 3D Slicer.** The Slicer extension's CI launches an
  actual headless Slicer and runs the full pipeline on every push — not just lint
  and compile.
- **Typed and validated end-to-end.** Pydantic models throughout, `py.typed`,
  strict `mypy`, `ruff` lint/format — enforced in CI across Python 3.10–3.12.
- **Reproducible & published.** Live on PyPI via OIDC **Trusted Publishing** (no
  stored secrets); a **mkdocs** documentation site; branch protection requiring
  green CI on both repos.
- **Synthetic test data, never real patients.** Every test builds deterministic
  synthetic DICOM, so the whole suite runs anywhere with no PHI.

### Tech stack

| Area | Tools |
|---|---|
| Engine | Python 3.10+, SimpleITK, pynrrd, nibabel, Pydantic, Typer, Rich |
| Native tool | C++17, ITK, CMake |
| GUI | 3D Slicer scripted module (Python / Qt) |
| Quality | pytest, ruff, mypy, pre-commit, GitHub Actions CI |
| Delivery | PyPI (Trusted Publishing), mkdocs-material docs, GitHub Pages |

---

## Licensing (open-core)

- **`slicer-forge`** (the Slicer extension) — Apache-2.0, fully open.
- **`dicom-forge` / `dicom-anvil`** (the engine) — **PolyForm Noncommercial 1.0.0**:
  free for research, education, and personal use; commercial use requires a
  separate license.

---

## Links

- **Engine repo:** https://github.com/DaCameraGirl/dicom-forge
- **Slicer extension repo:** https://github.com/DaCameraGirl/slicer-forge
- **PyPI:** https://pypi.org/project/dicom-anvil/ — `pip install "dicom-anvil[convert]"`
- **Documentation:** https://dacameragirl.github.io/dicom-forge/
