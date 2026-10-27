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
  <a href="README.zh-CN.md"><img src="https://img.shields.io/badge/🇨🇳_中文-2dd4bf?style=for-the-badge" alt="中文"/></a>
    <a href="README.ja.md"><img src="https://img.shields.io/badge/🇯🇵_日本語-1e293b?style=for-the-badge" alt="日本語"/></a>
    <a href="README.ko.md"><img src="https://img.shields.io/badge/🇰🇷_한국어-1e293b?style=for-the-badge" alt="한국어"/></a>
    <a href="README.it.md"><img src="https://img.shields.io/badge/🇮🇹_Italiano-1e293b?style=for-the-badge" alt="Italiano"/></a>
    <a href="README.ar.md"><img src="https://img.shields.io/badge/🇸🇦_العربية-1e293b?style=for-the-badge" alt="العربية"/></a>
</p>

> **Translation note:** this translation has not been reviewed by a native speaker. The [English README](README.md) is authoritative, especially for the privacy limitations.

<p align="center">
  <img src="docs/assets/deid-scanner.svg" alt="DICOM 去标识动画 — X 光扫描与病历姓名涂黑" width="520"/>
</p>

<p align="center">
  <a href="https://github.com/DaCameraGirl/dicom-forge/actions/workflows/ci.yml"><img src="https://github.com/DaCameraGirl/dicom-forge/actions/workflows/ci.yml/badge.svg" alt="CI"/></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python"/></a>
  <a href="https://dacameragirl.github.io/dicom-forge/"><img src="https://img.shields.io/badge/docs-dacameragirl.github.io-2dd4bf.svg" alt="文档"/></a>
  <img src="https://img.shields.io/badge/license-PolyForm%20Noncommercial%201.0.0-orange.svg" alt="License"/>
</p>

**面向科研的医学影像流水线，为 [3D Slicer](https://www.slicer.org/) 和 [ITK-SNAP](http://www.itksnap.org/) 准备 DICOM。**

`dicom-forge` 接收 DICOM 文件夹，**去标识化**（从元数据中移除患者姓名和 ID），进行**质量控制**并**转换**为 NIfTI、NRRD 及 Slicer 分割格式。每次运行生成可序列化审计记录。

双仓库系统的无头核心；配套 [`slicer-forge`](https://github.com/DaCameraGirl/slicer-forge) 提供 3D Slicer 扩展 GUI。

> 📌 **初次了解？** 阅读 [**项目展示**](SHOWCASE.md)。

---

## 为何存在

真实流水线将**可测试的无头核心**与**薄 GUI** 分离。`dicom-forge` 可在无 Slicer 的 CI 中测试，支持 CLI、Python 或 Slicer 控制台。

## 功能

- 摄取、去标识（三级）、QC、转换、分割、Pydantic、Rich CLI、`dicom-probe`

## 安装

```bash
pip install dicom-anvil            # core (ingest, de-id, QC)
pip install "dicom-anvil[convert]" # + SimpleITK/pynrrd/nibabel for conversion
```

> PyPI 包名 `dicom-anvil`，导入 `dicomforge`。

> SimpleITK 为**可选扩展**。

## 快速开始

### 命令行

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

## 流水线顺序

```
ingest ──> burned-in check ──> de-identify ──> QC ──> convert
```

去标识在转换**之前**，**内存处理**，源 DICOM 不被修改。

> ⚠️ **并非经过验证的匿名化工具。** 仅对 DICOM 头信息去标识；像素数据从不分析。元数据表明存在烧录文字的序列会被拒绝，但其他烧录在图像中的文字无法检测。未经法规或临床验证。请参阅[去标识策略](docs/deidentification-policy.md)（英文），并在共享前审查输出。

## 开发

```bash
python -m venv .venv && . .venv/Scripts/activate   # Windows
pip install -e ".[dev,convert]"
pytest                      # run the suite (synthetic DICOM, no real data needed)
ruff check . && mypy        # lint + type-check
```

## 许可证

[PolyForm Noncommercial License 1.0.0](LICENSE) © Angela Hudson
