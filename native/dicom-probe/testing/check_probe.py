"""Validate dicom-probe's JSON output against the known synthetic series.

Usage:
    python check_probe.py <probe-output.json>

Exits non-zero (with a message) on the first failed assertion, so the CI step
fails loudly if the native tool's geometry disagrees with what make_series.py
wrote.
"""

from __future__ import annotations

import json
import math
import sys


def _approx(actual: float, expected: float, tol: float = 1e-3) -> bool:
    return math.isclose(actual, expected, abs_tol=tol)


def main(path: str) -> None:
    with open(path, encoding="utf-8") as handle:
        report = json.load(handle)

    failures: list[str] = []

    if not report.get("ok"):
        sys.exit(f"probe reported failure: {report.get('error', '<no message>')}")

    if report["slices"] != 6:
        failures.append(f"slices: expected 6, got {report['slices']}")
    if report["series_found"] < 1:
        failures.append(f"series_found: expected >=1, got {report['series_found']}")

    if report["dimensions"] != [16, 16, 6]:
        failures.append(f"dimensions: expected [16, 16, 6], got {report['dimensions']}")

    sx, sy, sz = report["spacing"]
    if not (_approx(sx, 0.7) and _approx(sy, 0.7) and _approx(sz, 1.0)):
        failures.append(f"spacing: expected [0.7, 0.7, 1.0], got {report['spacing']}")

    intensity = report["intensity"]
    if not intensity["max"] > intensity["min"]:
        failures.append(f"intensity: max should exceed min, got {intensity}")

    if len(report["direction"]) != 9:
        failures.append(f"direction: expected 9 cosines, got {len(report['direction'])}")

    if failures:
        sys.exit("dicom-probe output validation failed:\n  - " + "\n  - ".join(failures))

    print("dicom-probe output OK:", json.dumps(report))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python check_probe.py <probe-output.json>")
    main(sys.argv[1])
