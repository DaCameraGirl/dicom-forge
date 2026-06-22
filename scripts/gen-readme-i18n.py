#!/usr/bin/env python3
"""Generate README.*.md translations for dicom-forge from structured strings."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACCENT = "2dd4bf"
INACTIVE = "1e293b"
LANGS = ("es", "fr", "de", "pt-BR", "zh-CN", "ja", "ko", "it", "ar")

LANG_BAR = {
    "en": ("English", "🇺🇸"),
    "es": ("Español", "🇪🇸"),
    "fr": ("Français", "🇫🇷"),
    "de": ("Deutsch", "🇩🇪"),
    "pt-BR": ("Português", "🇧🇷"),
    "zh-CN": ("中文", "🇨🇳"),
    "ja": ("日本語", "🇯🇵"),
    "ko": ("한국어", "🇰🇷"),
    "it": ("Italiano", "🇮🇹"),
    "ar": ("العربية", "🇸🇦"),
}

T: dict[str, dict[str, str]] = {
    "en": {
        "title": "dicom-forge",
        "tagline": "**An enterprise-grade medical-imaging pipeline that prepares DICOM for [3D Slicer](https://www.slicer.org/) and [ITK-SNAP](http://www.itksnap.org/).**",
        "intro": "`dicom-forge` takes a folder of DICOM, **de-identifies** it (strips patient names and IDs from headers), runs **quality control**, and **converts** it into formats clinical-research viewers load natively — NIfTI (`.nii.gz`), NRRD (`.nrrd`), and Slicer's segmentation format (`.seg.nrrd`). Every run produces a serialisable audit record.",
        "companion": "It is the headless core of a two-repo system; its companion, [`slicer-forge`](https://github.com/DaCameraGirl/slicer-forge), wraps it in a 3D Slicer extension GUI.",
        "showcase": "> 📌 **New here?** Read the [**project showcase**](SHOWCASE.md) for the big picture — the problem, the architecture, who it's for, and the engineering highlights.",
        "anim_alt": "Animated DICOM de-identification — x-ray scan with patient names redacted from paperwork",
        "live_docs": "Docs",
        "why_h": "## Why this exists",
        "why": "Real imaging pipelines separate a **testable, headless core** from a **thin GUI**. 3D Slicer itself is built this way: ITK/VTK do the work, the GUI is a shell on top. `dicom-forge` is that core — so the logic is unit-tested in CI **without** needing Slicer installed, and the same code runs from the command line, from Python, or inside Slicer's Python console.",
        "feat_h": "## Features",
        "feat": """- **Ingestion** — recursive DICOM discovery, series grouping, geometry-aware slice ordering (handles oblique acquisitions), rescale-slope/intercept applied (CT in HU).
- **De-identification** — three escalating levels modelled on the DICOM PS3.15 Basic Profile, with deterministic salted-hash pseudonymisation of `PatientID`.
- **Quality control** — slice count, geometry consistency, slice-spacing regularity, and intensity statistics, split into blocking errors vs. non-blocking warnings.
- **Conversion** — geometry-preserving export to NIfTI / NRRD via SimpleITK (the ITK core shared with Slicer & ITK-SNAP).
- **Segmentation** — write Slicer-native `.seg.nrrd` label maps with named, coloured segments.
- **Typed & validated** — Pydantic models everywhere, `py.typed`, strict mypy.
- **Two interfaces** — a Rich CLI (`dicomforge`) and a clean Python API.
- **Native ITK pre-flight** — a companion C++/ITK CLI, [`dicom-probe`](native/dicom-probe/), reads a series through ITK's own GDCM path (the engine under Slicer/ITK-SNAP) and reports the true volume geometry as JSON.""",
        "install_h": "## Installation",
        "install_note1": "> **Names:** the package installs as `dicom-anvil` (the PyPI name `dicom-forge` was already taken) and imports as `dicomforge`; the repository stays `dicom-forge`.",
        "install_note2": "> The conversion stack (SimpleITK et al.) is an **optional extra** so the core stays lightweight and CI-friendly. Calling a conversion function without it raises a clear `MissingDependencyError` telling you exactly what to install.",
        "quick_h": "## Quick start",
        "cli_h": "### Command line",
        "py_h": "### Python",
        "pipe_h": "## Pipeline order (and why it matters)",
        "pipe_note": "De-identification runs **before** conversion, so any file written to disk is already free of direct identifiers. De-id is performed **in memory** — your source DICOM is never modified.",
        "warn": "> ⚠️ **De-identification is risk reduction, not a legal guarantee.** Burned-in pixel annotations and private vendor tags can still carry PHI. Always review output before releasing it outside a controlled environment.",
        "dev_h": "## Development",
        "lic_h": "## License",
        "lic": "[PolyForm Noncommercial License 1.0.0](LICENSE) © Angela Hudson\n\nNoncommercial use — personal, research, educational, and other noncommercial purposes as defined by the license — is free. **Any commercial use requires a separate license from the copyright holder.** See [LICENSE](LICENSE) for the full terms, or open an issue to ask about commercial licensing.",
    },
    "es": {
        "title": "dicom-forge",
        "tagline": "**Pipeline de imágenes médicas de nivel empresarial que prepara DICOM para [3D Slicer](https://www.slicer.org/) e [ITK-SNAP](http://www.itksnap.org/).**",
        "intro": "`dicom-forge` toma una carpeta de DICOM, la **desidentifica** (elimina nombres e IDs del paciente en las cabeceras), ejecuta **control de calidad** y **convierte** a formatos que los visores clínicos cargan de forma nativa — NIfTI (`.nii.gz`), NRRD (`.nrrd`) y segmentación de Slicer (`.seg.nrrd`). Cada ejecución genera un registro de auditoría serializable.",
        "companion": "Es el núcleo sin interfaz de un sistema de dos repos; su compañero, [`slicer-forge`](https://github.com/DaCameraGirl/slicer-forge), lo envuelve en una extensión GUI de 3D Slicer.",
        "showcase": "> 📌 **¿Nuevo aquí?** Lee el [**showcase del proyecto**](SHOWCASE.md) — el problema, la arquitectura, el público objetivo y los aspectos técnicos.",
        "anim_alt": "Desidentificación DICOM animada — escáner con nombres de paciente tachados en el papeleo",
        "live_docs": "Documentación",
        "why_h": "## Por qué existe",
        "why": "Los pipelines reales separan un **núcleo headless comprobable** de una **GUI delgada**. 3D Slicer funciona así: ITK/VTK hacen el trabajo; la GUI es una capa. `dicom-forge` es ese núcleo — probado en CI **sin** instalar Slicer, y usable desde CLI, Python o la consola de Slicer.",
        "feat_h": "## Funciones",
        "feat": """- **Ingesta** — descubrimiento recursivo, agrupación de series, orden geométrico de cortes (adquisiciones oblicuas), rescale-slope/intercept (TC en HU).
- **Desidentificación** — tres niveles según el Perfil Básico DICOM PS3.15, con seudonimización determinista de `PatientID`.
- **Control de calidad** — conteo de cortes, geometría, espaciado e intensidad; errores bloqueantes vs. advertencias.
- **Conversión** — exportación a NIfTI / NRRD vía SimpleITK (núcleo ITK compartido con Slicer e ITK-SNAP).
- **Segmentación** — mapas `.seg.nrrd` nativos de Slicer con segmentos nombrados y coloreados.
- **Tipado y validación** — modelos Pydantic, `py.typed`, mypy estricto.
- **Dos interfaces** — CLI Rich (`dicomforge`) y API Python limpia.
- **Pre-vuelo ITK nativo** — CLI C++/ITK [`dicom-probe`](native/dicom-probe/) reporta geometría del volumen como JSON.""",
        "install_h": "## Instalación",
        "install_note1": "> **Nombres:** el paquete se instala como `dicom-anvil` (PyPI) e importa como `dicomforge`; el repositorio sigue siendo `dicom-forge`.",
        "install_note2": "> La pila de conversión (SimpleITK, etc.) es un **extra opcional** para mantener el núcleo ligero. Sin él, verás un `MissingDependencyError` claro.",
        "quick_h": "## Inicio rápido",
        "cli_h": "### Línea de comandos",
        "py_h": "### Python",
        "pipe_h": "## Orden del pipeline (y por qué importa)",
        "pipe_note": "La desidentificación corre **antes** de la conversión, así que todo archivo en disco ya está libre de identificadores directos. Se hace **en memoria** — el DICOM fuente nunca se modifica.",
        "warn": "> ⚠️ **La desidentificación reduce riesgo, no garantiza cumplimiento legal.** Anotaciones quemadas en píxeles y tags privados pueden conservar PHI. Revise la salida antes de compartirla.",
        "dev_h": "## Desarrollo",
        "lic_h": "## Licencia",
        "lic": "[PolyForm Noncommercial License 1.0.0](LICENSE) © Angela Hudson\n\nUso no comercial gratuito. **Uso comercial requiere licencia separada.** Ver [LICENSE](LICENSE) o abra un issue.",
    },
    "fr": {
        "title": "dicom-forge",
        "tagline": "**Pipeline d'imagerie médicale prêt pour la production, préparant le DICOM pour [3D Slicer](https://www.slicer.org/) et [ITK-SNAP](http://www.itksnap.org/).**",
        "intro": "`dicom-forge` prend un dossier DICOM, le **dé-identifie** (retire noms et identifiants patient des en-têtes), exécute un **contrôle qualité** et **convertit** vers NIfTI (`.nii.gz`), NRRD (`.nrrd`) et segmentation Slicer (`.seg.nrrd`). Chaque exécution produit un journal d'audit sérialisable.",
        "companion": "C'est le cœur headless d'un système à deux dépôts ; le compagnon [`slicer-forge`](https://github.com/DaCameraGirl/slicer-forge) l'enveloppe dans une extension 3D Slicer.",
        "showcase": "> 📌 **Nouveau ?** Lisez le [**showcase**](SHOWCASE.md) — problème, architecture, public et points techniques.",
        "anim_alt": "Dé-identification DICOM animée — scanner et noms patient barrés sur le dossier",
        "live_docs": "Documentation",
        "why_h": "## Pourquoi ce projet",
        "why": "Les vrais pipelines séparent un **noyau headless testable** d'une **GUI fine**. 3D Slicer fonctionne ainsi. `dicom-forge` est ce noyau — testé en CI **sans** Slicer, utilisable en CLI, Python ou console Slicer.",
        "feat_h": "## Fonctionnalités",
        "feat": """- **Ingestion** — découverte récursive, regroupement de séries, ordre géométrique des coupes.
- **Dé-identification** — trois niveaux selon le profil DICOM PS3.15, pseudonymisation de `PatientID`.
- **Contrôle qualité** — géométrie, espacement, intensité ; erreurs bloquantes vs avertissements.
- **Conversion** — export NIfTI / NRRD via SimpleITK.
- **Segmentation** — cartes `.seg.nrrd` Slicer.
- **Typé et validé** — Pydantic, `py.typed`, mypy strict.
- **Deux interfaces** — CLI Rich (`dicomforge`) et API Python.
- **Pré-vol ITK** — [`dicom-probe`](native/dicom-probe/) en C++/ITK.""",
        "install_h": "## Installation",
        "install_note1": "> **Noms :** paquet PyPI `dicom-anvil`, import `dicomforge`, dépôt `dicom-forge`.",
        "install_note2": "> SimpleITK est un **extra optionnel** pour un noyau léger.",
        "quick_h": "## Démarrage rapide",
        "cli_h": "### Ligne de commande",
        "py_h": "### Python",
        "pipe_h": "## Ordre du pipeline",
        "pipe_note": "La dé-identification précède la conversion ; traitement **en mémoire** — la source n'est jamais modifiée.",
        "warn": "> ⚠️ **Réduction de risque, pas garantie juridique.** Vérifiez toujours la sortie avant diffusion.",
        "dev_h": "## Développement",
        "lic_h": "## Licence",
        "lic": "[PolyForm Noncommercial License 1.0.0](LICENSE) © Angela Hudson — usage non commercial gratuit ; **licence commerciale séparée requise.**",
    },
    "de": {
        "title": "dicom-forge",
        "tagline": "**Enterprise-Pipeline für medizinische Bildgebung — bereitet DICOM für [3D Slicer](https://www.slicer.org/) und [ITK-SNAP](http://www.itksnap.org/) vor.**",
        "intro": "`dicom-forge` nimmt einen DICOM-Ordner, **de-identifiziert** ihn (entfernt Patientennamen und IDs aus Headern), führt **Qualitätskontrolle** durch und **konvertiert** nach NIfTI, NRRD und Slicer-Segmentierung. Jeder Lauf erzeugt einen serialisierbaren Audit-Datensatz.",
        "companion": "Headless-Kern eines Zwei-Repo-Systems; [`slicer-forge`](https://github.com/DaCameraGirl/slicer-forge) ist die 3D-Slicer-GUI.",
        "showcase": "> 📌 **Neu hier?** [**Showcase**](SHOWCASE.md) lesen — Problem, Architektur, Zielgruppe.",
        "anim_alt": "Animierte DICOM-De-Identifizierung — Röntgen und geschwärzte Patientennamen",
        "live_docs": "Dokumentation",
        "why_h": "## Warum es existiert",
        "why": "Echte Pipelines trennen **testbaren Headless-Kern** und **dünne GUI**. `dicom-forge` ist dieser Kern — CI ohne Slicer, nutzbar per CLI, Python oder Slicer-Konsole.",
        "feat_h": "## Funktionen",
        "feat": """- **Ingestion**, **De-Identifizierung** (3 Stufen, DICOM PS3.15), **QC**, **Konvertierung**, **Segmentierung**
- Pydantic, mypy, Rich-CLI (`dicomforge`), Python-API, [`dicom-probe`](native/dicom-probe/)""",
        "install_h": "## Installation",
        "install_note1": "> PyPI-Name: `dicom-anvil`, Import: `dicomforge`.",
        "install_note2": "> SimpleITK ist ein **optionales Extra**.",
        "quick_h": "## Schnellstart",
        "cli_h": "### Kommandozeile",
        "py_h": "### Python",
        "pipe_h": "## Pipeline-Reihenfolge",
        "pipe_note": "De-ID **vor** Konvertierung, **im Speicher** — Quell-DICOM unverändert.",
        "warn": "> ⚠️ **Risikoreduktion, keine Rechtsgarantie.** Ausgabe vor Freigabe prüfen.",
        "dev_h": "## Entwicklung",
        "lic_h": "## Lizenz",
        "lic": "[PolyForm Noncommercial License 1.0.0](LICENSE) © Angela Hudson — nichtkommerziell frei; **kommerziell separate Lizenz.**",
    },
    "pt-BR": {
        "title": "dicom-forge",
        "tagline": "**Pipeline de imagens médicas que prepara DICOM para [3D Slicer](https://www.slicer.org/) e [ITK-SNAP](http://www.itksnap.org/).**",
        "intro": "`dicom-forge` recebe uma pasta DICOM, **desidentifica** (remove nomes e IDs do paciente), faz **controle de qualidade** e **converte** para NIfTI, NRRD e `.seg.nrrd`. Cada execução gera auditoria serializável.",
        "companion": "Núcleo headless; [`slicer-forge`](https://github.com/DaCameraGirl/slicer-forge) é a GUI no 3D Slicer.",
        "showcase": "> 📌 **Novo?** Veja o [**showcase**](SHOWCASE.md).",
        "anim_alt": "Desidentificação DICOM animada — raio-X e nomes riscados no formulário",
        "live_docs": "Documentação",
        "why_h": "## Por que existe",
        "why": "Pipelines reais separam **núcleo testável** e **GUI fina**. `dicom-forge` roda em CI sem Slicer — CLI, Python ou console do Slicer.",
        "feat_h": "## Recursos",
        "feat": "- Ingestão, desidentificação (3 níveis), QC, conversão, segmentação, Pydantic, CLI `dicomforge`, [`dicom-probe`](native/dicom-probe/)",
        "install_h": "## Instalação",
        "install_note1": "> Pacote PyPI: `dicom-anvil`, import: `dicomforge`.",
        "install_note2": "> SimpleITK é **extra opcional**.",
        "quick_h": "## Início rápido",
        "cli_h": "### Linha de comando",
        "py_h": "### Python",
        "pipe_h": "## Ordem do pipeline",
        "pipe_note": "Desidentificação **antes** da conversão, **em memória**.",
        "warn": "> ⚠️ **Redução de risco, não garantia legal.** Revise a saída.",
        "dev_h": "## Desenvolvimento",
        "lic_h": "## Licença",
        "lic": "[PolyForm Noncommercial License 1.0.0](LICENSE) © Angela Hudson",
    },
    "zh-CN": {
        "title": "dicom-forge",
        "tagline": "**企业级医学影像流水线，为 [3D Slicer](https://www.slicer.org/) 和 [ITK-SNAP](http://www.itksnap.org/) 准备 DICOM。**",
        "intro": "`dicom-forge` 接收 DICOM 文件夹，**去标识化**（从元数据中移除患者姓名和 ID），进行**质量控制**并**转换**为 NIfTI、NRRD 及 Slicer 分割格式。每次运行生成可序列化审计记录。",
        "companion": "双仓库系统的无头核心；配套 [`slicer-forge`](https://github.com/DaCameraGirl/slicer-forge) 提供 3D Slicer 扩展 GUI。",
        "showcase": "> 📌 **初次了解？** 阅读 [**项目展示**](SHOWCASE.md)。",
        "anim_alt": "DICOM 去标识动画 — X 光扫描与病历姓名涂黑",
        "live_docs": "文档",
        "why_h": "## 为何存在",
        "why": "真实流水线将**可测试的无头核心**与**薄 GUI** 分离。`dicom-forge` 可在无 Slicer 的 CI 中测试，支持 CLI、Python 或 Slicer 控制台。",
        "feat_h": "## 功能",
        "feat": "- 摄取、去标识（三级）、QC、转换、分割、Pydantic、Rich CLI、`dicom-probe`",
        "install_h": "## 安装",
        "install_note1": "> PyPI 包名 `dicom-anvil`，导入 `dicomforge`。",
        "install_note2": "> SimpleITK 为**可选扩展**。",
        "quick_h": "## 快速开始",
        "cli_h": "### 命令行",
        "py_h": "### Python",
        "pipe_h": "## 流水线顺序",
        "pipe_note": "去标识在转换**之前**，**内存处理**，源 DICOM 不被修改。",
        "warn": "> ⚠️ **去标识是降风险，非法律保证。** 共享前请审查输出。",
        "dev_h": "## 开发",
        "lic_h": "## 许可证",
        "lic": "[PolyForm Noncommercial License 1.0.0](LICENSE) © Angela Hudson",
    },
    "ja": {
        "title": "dicom-forge",
        "tagline": "**[3D Slicer](https://www.slicer.org/) と [ITK-SNAP](http://www.itksnap.org/) 向けのエンタープライズ DICOM パイプライン。**",
        "intro": "`dicom-forge` は DICOM フォルダを **匿名化**（患者名・ID をヘッダから除去）し、**QC** を実行して NIfTI / NRRD / `.seg.nrrd` に **変換**します。各実行で監査レコードを生成します。",
        "companion": "ヘッドレス中核。GUI は [`slicer-forge`](https://github.com/DaCameraGirl/slicer-forge)。",
        "showcase": "> 📌 **初めて？** [**ショーケース**](SHOWCASE.md) をご覧ください。",
        "anim_alt": "DICOM 匿名化アニメーション — X線と書類の名前消去",
        "live_docs": "ドキュメント",
        "why_h": "## なぜ作ったか",
        "why": "本番パイプラインは **テスト可能なコア** と **薄い GUI** を分離します。Slicer なしで CI テスト可能です。",
        "feat_h": "## 機能",
        "feat": "- 取り込み、匿名化（3段階）、QC、変換、セグメンテーション、Pydantic、CLI `dicomforge`",
        "install_h": "## インストール",
        "install_note1": "> PyPI: `dicom-anvil`、import: `dicomforge`。",
        "install_note2": "> SimpleITK は**オプション extra**。",
        "quick_h": "## クイックスタート",
        "cli_h": "### コマンドライン",
        "py_h": "### Python",
        "pipe_h": "## パイプライン順序",
        "pipe_note": "匿名化は変換**前**、**メモリ内**処理。",
        "warn": "> ⚠️ **リスク低減であり法的保証ではありません。**",
        "dev_h": "## 開発",
        "lic_h": "## ライセンス",
        "lic": "[PolyForm Noncommercial License 1.0.0](LICENSE) © Angela Hudson",
    },
    "ko": {
        "title": "dicom-forge",
        "tagline": "**[3D Slicer](https://www.slicer.org/) 및 [ITK-SNAP](http://www.itksnap.org/)용 엔터프라이즈 DICOM 파이프라인.**",
        "intro": "`dicom-forge`는 DICOM 폴더를 **비식별화**(환자 이름·ID 제거)하고 **QC** 후 NIfTI/NRRD/`.seg.nrrd`로 **변환**합니다.",
        "companion": "헤드리스 코어; GUI는 [`slicer-forge`](https://github.com/DaCameraGirl/slicer-forge).",
        "showcase": "> 📌 **처음이신가요?** [**쇼케이스**](SHOWCASE.md)를 읽어보세요.",
        "anim_alt": "DICOM 비식별 애니메이션 — X선과 서류 이름 삭제",
        "live_docs": "문서",
        "why_h": "## 왜 만들었나",
        "why": "실제 파이프라인은 **테스트 가능한 코어**와 **얇은 GUI**를 분리합니다. Slicer 없이 CI 가능.",
        "feat_h": "## 기능",
        "feat": "- 수집, 비식별(3단계), QC, 변환, 세그멘테이션, Pydantic, CLI `dicomforge`",
        "install_h": "## 설치",
        "install_note1": "> PyPI: `dicom-anvil`, import: `dicomforge`.",
        "install_note2": "> SimpleITK는 **선택 extra**.",
        "quick_h": "## 빠른 시작",
        "cli_h": "### 명령줄",
        "py_h": "### Python",
        "pipe_h": "## 파이프라인 순서",
        "pipe_note": "비식별은 변환 **전**, **메모리** 처리.",
        "warn": "> ⚠️ **위험 감소이지 법적 보장이 아닙니다.**",
        "dev_h": "## 개발",
        "lic_h": "## 라이선스",
        "lic": "[PolyForm Noncommercial License 1.0.0](LICENSE) © Angela Hudson",
    },
    "it": {
        "title": "dicom-forge",
        "tagline": "**Pipeline di imaging medico per [3D Slicer](https://www.slicer.org/) e [ITK-SNAP](http://www.itksnap.org/).**",
        "intro": "`dicom-forge` prende una cartella DICOM, la **de-identifica** (rimuove nomi e ID paziente), esegue **QC** e **converte** in NIfTI, NRRD e `.seg.nrrd`.",
        "companion": "Nucleo headless; [`slicer-forge`](https://github.com/DaCameraGirl/slicer-forge) è la GUI Slicer.",
        "showcase": "> 📌 **Nuovo?** Leggi lo [**showcase**](SHOWCASE.md).",
        "anim_alt": "De-identificazione DICOM animata — radiografia e nomi oscurati",
        "live_docs": "Documentazione",
        "why_h": "## Perché esiste",
        "why": "Separa **core testabile** e **GUI sottile**. Testabile in CI senza Slicer.",
        "feat_h": "## Funzionalità",
        "feat": "- Ingestione, de-id (3 livelli), QC, conversione, segmentazione, Pydantic, CLI `dicomforge`",
        "install_h": "## Installazione",
        "install_note1": "> PyPI: `dicom-anvil`, import: `dicomforge`.",
        "install_note2": "> SimpleITK **extra opzionale**.",
        "quick_h": "## Avvio rapido",
        "cli_h": "### Riga di comando",
        "py_h": "### Python",
        "pipe_h": "## Ordine pipeline",
        "pipe_note": "De-id **prima** della conversione, **in memoria**.",
        "warn": "> ⚠️ **Riduzione del rischio, non garanzia legale.**",
        "dev_h": "## Sviluppo",
        "lic_h": "## Licenza",
        "lic": "[PolyForm Noncommercial License 1.0.0](LICENSE) © Angela Hudson",
    },
    "ar": {
        "title": "dicom-forge",
        "tagline": "**خط أنابيب تصوير طبي على مستوى المؤسسات لـ [3D Slicer](https://www.slicer.org/) و [ITK-SNAP](http://www.itksnap.org/).**",
        "intro": "يأخذ `dicom-forge` مجلد DICOM و**يزيل الهوية** (أسماء ومعرّفات المريض من الرؤوس) ويجري **مراقبة الجودة** و**يحوّل** إلى NIfTI وNRRD و`.seg.nrrd`.",
        "companion": "النواة بدون واجهة؛ [`slicer-forge`](https://github.com/DaCameraGirl/slicer-forge) هي واجهة Slicer.",
        "showcase": "> 📌 **جديد؟** اقرأ [**العرض**](SHOWCASE.md).",
        "anim_alt": "إزالة هوية DICOM متحركة — أشعة سينية وأسماء محذوفة من الأوراق",
        "live_docs": "الوثائق",
        "why_h": "## لماذا يوجد",
        "why": "يفصل **نواة قابلة للاختبار** عن **واجهة رقيقة**. يُختبر في CI بدون Slicer.",
        "feat_h": "## الميزات",
        "feat": "- استيعاب، إزالة هوية (3 مستويات)، QC، تحويل، تجزئة، Pydantic، CLI `dicomforge`",
        "install_h": "## التثبيت",
        "install_note1": "> PyPI: `dicom-anvil`، الاستيراد: `dicomforge`.",
        "install_note2": "> SimpleITK **إضافة اختيارية**.",
        "quick_h": "## بداية سريعة",
        "cli_h": "### سطر الأوامر",
        "py_h": "### بايثون",
        "pipe_h": "## ترتيب الخط أنابيب",
        "pipe_note": "إزالة الهوية **قبل** التحويل، **في الذاكرة**.",
        "warn": "> ⚠️ **تقليل مخاطر وليس ضماناً قانونياً.**",
        "dev_h": "## التطوير",
        "lic_h": "## الترخيص",
        "lic": "[PolyForm Noncommercial License 1.0.0](LICENSE) © Angela Hudson",
    },
}

def lang_bar(active: str) -> str:
    rows = []
    keys = list(LANG_BAR.keys())
    for row_start in (0, 5):
        parts = []
        for code, (label, flag) in [(k, LANG_BAR[k]) for k in keys[row_start : row_start + 5]]:
            href = "README.md" if code == "en" else f"README.{code}.md"
            color = ACCENT if code == active else INACTIVE
            parts.append(
                f'  <a href="{href}"><img src="https://img.shields.io/badge/{flag}_{label.replace(" ", "_")}-{color}?style=for-the-badge" alt="{label}"/></a>'
            )
        rows.append("<p align=\"center\">\n" + "\n  ".join(parts) + "\n</p>")
    return "\n".join(rows)


def render(lang: str) -> str:
    t = T[lang]
    active_file = "en" if lang == "en" else lang
    badges = f"""<p align="center">
  <a href="https://github.com/DaCameraGirl/dicom-forge/actions/workflows/ci.yml"><img src="https://github.com/DaCameraGirl/dicom-forge/actions/workflows/ci.yml/badge.svg" alt="CI"/></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python"/></a>
  <a href="https://dacameragirl.github.io/dicom-forge/"><img src="https://img.shields.io/badge/docs-dacameragirl.github.io-{ACCENT}.svg" alt="{t['live_docs']}"/></a>
  <img src="https://img.shields.io/badge/license-PolyForm%20Noncommercial%201.0.0-orange.svg" alt="License"/>
</p>"""
    return f"""<p align="center">
  <img src="docs/assets/readme-hero.svg" alt="DICOM Forge — de-identify, QC, convert" width="100%"/>
</p>

# {t['title']}

{lang_bar(active_file)}

<p align="center">
  <img src="docs/assets/deid-scanner.svg" alt="{t['anim_alt']}" width="520"/>
</p>

{badges}

{t['tagline']}

{t['intro']}

{t['companion']}

{t['showcase']}

---

{t['why_h']}

{t['why']}

{t['feat_h']}

{t['feat']}

{t['install_h']}

```bash
pip install dicom-anvil            # core (ingest, de-id, QC)
pip install "dicom-anvil[convert]" # + SimpleITK/pynrrd/nibabel for conversion
```

{t['install_note1']}

{t['install_note2']}

{t['quick_h']}

{t['cli_h']}

```bash
# List the series in a folder
dicomforge inspect ./study

# Run QC and print a report
dicomforge qc ./study

# Full pipeline: de-identify -> QC -> convert to Slicer NRRD
dicomforge convert ./study ./out/patient01 --format nrrd --deid-level moderate
```

{t['py_h']}

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

{t['pipe_h']}

```
ingest ──> de-identify ──> QC ──> convert
```

{t['pipe_note']}

{t['warn']}

{t['dev_h']}

```bash
python -m venv .venv && . .venv/Scripts/activate   # Windows
pip install -e ".[dev,convert]"
pytest                      # run the suite (synthetic DICOM, no real data needed)
ruff check . && mypy        # lint + type-check
```

{t['lic_h']}

{t['lic']}
"""


def main() -> None:
    (ROOT / "README.md").write_text(render("en"), encoding="utf-8")
    for lang in LANGS:
        (ROOT / f"README.{lang}.md").write_text(render(lang), encoding="utf-8")
    print(f"Wrote README.md + {len(LANGS)} translations")


if __name__ == "__main__":
    main()