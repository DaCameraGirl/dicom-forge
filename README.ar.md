<p align="center">
  <img src="docs/assets/readme-hero.svg" alt="DICOM Forge — de-identify, QC, convert" width="100%"/>
</p>

# dicom-forge

<p align="center">
  <a href="README.md"><img src="https://img.shields.io/badge/🇺🇸_English-1e293b?style=for-the-badge" alt="English"/></a>
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
    <a href="README.ar.md"><img src="https://img.shields.io/badge/🇸🇦_العربية-2dd4bf?style=for-the-badge" alt="العربية"/></a>
</p>

> **Translation note:** this translation has not been reviewed by a native speaker. The [English README](README.md) is authoritative, especially for the privacy limitations.

<p align="center">
  <img src="docs/assets/deid-scanner.svg" alt="إزالة هوية DICOM متحركة — أشعة سينية وأسماء محذوفة من الأوراق" width="520"/>
</p>

<p align="center">
  <a href="https://github.com/DaCameraGirl/dicom-forge/actions/workflows/ci.yml"><img src="https://github.com/DaCameraGirl/dicom-forge/actions/workflows/ci.yml/badge.svg" alt="CI"/></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python"/></a>
  <a href="https://dacameragirl.github.io/dicom-forge/"><img src="https://img.shields.io/badge/docs-dacameragirl.github.io-2dd4bf.svg" alt="الوثائق"/></a>
  <img src="https://img.shields.io/badge/license-PolyForm%20Noncommercial%201.0.0-orange.svg" alt="License"/>
</p>

**خط أنابيب تصوير طبي بحثي لـ [3D Slicer](https://www.slicer.org/) و [ITK-SNAP](http://www.itksnap.org/).**

يأخذ `dicom-forge` مجلد DICOM و**يزيل الهوية** (أسماء ومعرّفات المريض من الرؤوس) ويجري **مراقبة الجودة** و**يحوّل** إلى NIfTI وNRRD و`.seg.nrrd`.

النواة بدون واجهة؛ [`slicer-forge`](https://github.com/DaCameraGirl/slicer-forge) هي واجهة Slicer.

> 📌 **جديد؟** اقرأ [**العرض**](SHOWCASE.md).

---

## لماذا يوجد

يفصل **نواة قابلة للاختبار** عن **واجهة رقيقة**. يُختبر في CI بدون Slicer.

## الميزات

- استيعاب، إزالة هوية (3 مستويات)، QC، تحويل، تجزئة، Pydantic، CLI `dicomforge`

## التثبيت

```bash
pip install dicom-anvil            # core (ingest, de-id, QC)
pip install "dicom-anvil[convert]" # + SimpleITK/pynrrd/nibabel for conversion
```

> PyPI: `dicom-anvil`، الاستيراد: `dicomforge`.

> SimpleITK **إضافة اختيارية**.

## بداية سريعة

### سطر الأوامر

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

### بايثون

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

## ترتيب الخط أنابيب

```
ingest ──> burned-in check ──> de-identify ──> QC ──> convert
```

إزالة الهوية **قبل** التحويل، **في الذاكرة**.

> ⚠️ **ليست أداة مُتحقَّقاً منها لإخفاء الهوية.** تُزال الهوية من ترويسات DICOM فقط، ولا تُحلَّل بيانات البكسل أبداً. تُرفض السلاسل التي تشير بياناتها الوصفية إلى نص مطبوع داخل الصورة، لكن أي نص مطبوع آخر لا يُكتشف. لا يوجد تحقق تنظيمي أو سريري. راجع [سياسة إزالة الهوية](docs/deidentification-policy.md) (بالإنجليزية) وراجع المخرجات قبل مشاركتها.

## التطوير

```bash
python -m venv .venv && . .venv/Scripts/activate   # Windows
pip install -e ".[dev,convert]"
pytest                      # run the suite (synthetic DICOM, no real data needed)
ruff check . && mypy        # lint + type-check
```

## الترخيص

[PolyForm Noncommercial License 1.0.0](LICENSE) © Angela Hudson
