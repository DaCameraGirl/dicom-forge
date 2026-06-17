# dicom-forge

An enterprise-grade medical-imaging pipeline that prepares DICOM for
[3D Slicer](https://www.slicer.org/) and [ITK-SNAP](http://www.itksnap.org/).

It **ingests** DICOM, **de-identifies** PHI, runs **quality control**, and
**converts** to the formats research viewers load natively — NIfTI (`.nii.gz`),
NRRD (`.nrrd`), and Slicer's segmentation format (`.seg.nrrd`).

## Install

```bash
pip install "dicom-anvil[convert]"
```

> Installed as **`dicom-anvil`** (the name `dicom-forge` was already taken on
> PyPI); imported as **`dicomforge`**. The source repository is `dicom-forge`.

## 60-second tour

```bash
dicomforge inspect ./study                 # what's in this folder?
dicomforge qc ./study                       # is it analysis-ready?
dicomforge convert ./study ./out/case01 -f nrrd   # de-id -> QC -> convert
```

```python
from dicomforge import run_pipeline, PipelineConfig, OutputFormat

result = run_pipeline("./study", "./out/case01",
                      config=PipelineConfig(output_format=OutputFormat.NRRD))
print(result.model_dump_json(indent=2))
```

See [Concepts](concepts.md) for the pipeline design, the [CLI reference](cli.md)
for every command, and the [API reference](api.md) for the Python surface.

!!! warning "Patient data"
    De-identification is best-effort risk reduction, **not** a compliance guarantee.
    Never commit real patient data. See the project `SECURITY.md`.
