# Security & Data-Handling Policy

## Reporting a vulnerability

Please report security issues privately via GitHub's
[security advisory](https://github.com/DaCameraGirl/dicom-forge/security/advisories/new)
feature rather than a public issue. You will get an acknowledgement within a few days.

## Patient data — read this

`dicom-forge` processes medical images, which frequently contain Protected Health
Information (PHI).

- **Never commit real DICOM, NIfTI, or NRRD files to this repository.** The
  `.gitignore` blocks the common extensions, but treat that as a safety net, not a
  guarantee. Tests use **synthetic** data generated at runtime.
- **De-identification is best-effort risk reduction, not a compliance guarantee.**
  This software does not certify HIPAA, GDPR, or any other regulatory compliance,
  and it has not been clinically validated or certified.
  It de-identifies DICOM **headers** only. It never analyses or removes burned-in
  pixel annotations. It rejects series whose *metadata* signals that risk, but text
  burned into images without such a signal is not detected. See
  [the de-identification policy](docs/deidentification-policy.md).
- **Validate output** before any data leaves a controlled environment, and run
  de-identification inside that environment — never after data has been exported.

## Supported versions

The latest minor release on `main` receives security fixes.
