# Contributing to dicom-forge

Thanks for your interest! This project uses a branch + pull-request workflow with
CI gating every change.

## Setup

```bash
python -m venv .venv
. .venv/Scripts/activate          # Windows;  source .venv/bin/activate on Unix
pip install -e ".[dev,convert]"
pre-commit install
```

## Workflow

1. Open (or claim) an issue describing the change.
2. Branch from `main`: `git switch -c feature/<short-name>`.
3. Make the change **with tests**. Keep the diff focused.
4. Run the local gate before pushing:
   ```bash
   ruff check . && ruff format --check . && mypy && pytest
   ```
5. Update `CHANGELOG.md` under `[Unreleased]`.
6. Open a PR using the template; link the issue. CI must be green to merge.

## Standards

- **Typed**: all public functions are fully annotated; `mypy` runs in strict mode.
- **Tested**: new logic ships with tests. We use **synthetic DICOM only** — never
  commit real patient data (see [SECURITY.md](SECURITY.md)).
- **Lean core**: heavy native dependencies (SimpleITK, pynrrd, nibabel) live behind
  the `convert` extra. The core must import and run without them.
- **Style**: `ruff` (lint + format) is the single source of truth.

## Commit messages

Write descriptive messages explaining *what* and *why* (not "wip"/"fix").
Conventional Commit prefixes (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`) are
encouraged and feed nicely into release notes.
