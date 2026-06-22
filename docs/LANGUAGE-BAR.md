# README language bar

Both `dicom-forge` and `slicer-forge` READMEs use the same 10-language navigation pattern as Bettin2Win.

| File | Language |
|------|----------|
| `README.md` | English (active badge: `#2dd4bf` teal) |
| `README.es.md` | Spanish |
| `README.fr.md` | French |
| `README.de.md` | German |
| `README.pt-BR.md` | Portuguese (Brazil) |
| `README.zh-CN.md` | Chinese (Simplified) |
| `README.ja.md` | Japanese |
| `README.ko.md` | Korean |
| `README.it.md` | Italian |
| `README.ar.md` | Arabic |

Regenerate dicom-forge translations:

```bash
python scripts/gen-readme-i18n.py
```

Animated README graphics live in `docs/assets/`:

- `readme-hero.svg` — banner
- `deid-scanner.svg` — moving x-ray scan + paperwork name redaction