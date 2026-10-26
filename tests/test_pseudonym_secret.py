"""Regression tests for the pseudonymisation secret policy.

Audit 2026-10-26 (finding V5): PatientID pseudonyms were SHA-256("dicom-forge:" + id),
using a public default salt that neither the CLI nor the Slicer extension could change.
A structured MRN was recovered by enumeration in milliseconds. These tests pin the
replacement policy: keyed HMAC, a user-supplied secret (explicit or
``DICOMFORGE_PSEUDONYM_SECRET``), a random per-process key when none is configured, and
the secret never appearing in serialised config, audit records, or logs.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import traceback
from collections.abc import Iterator
from pathlib import Path

import pytest
from pydantic import ValidationError
from pydicom.dataset import Dataset

from dicomforge.config import PipelineConfig
from dicomforge.deidentify import deidentify_dataset, pseudonymise
from dicomforge.pipeline import run_pipeline

ENV = "DICOMFORGE_PSEUDONYM_SECRET"
SECRET = "unit-test-secret-0123456789abcdef"
ORIGINAL_ID = "MRN-0001"  # PatientID written by the conftest fixture


def legacy_public_pseudonym(value: str) -> str:
    """The pre-fix algorithm with the public default salt, reimplemented independently."""
    return "DF-" + hashlib.sha256(f"dicom-forge:{value}".encode()).hexdigest()[:16].upper()


class _Capture(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.DEBUG)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


@pytest.fixture
def dicomforge_logs() -> Iterator[_Capture]:
    """Capture every dicomforge log record (works even if the CLI disabled propagation)."""
    logger = logging.getLogger("dicomforge")
    handler = _Capture()
    old_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    yield handler
    logger.removeHandler(handler)
    logger.setLevel(old_level)


@pytest.fixture(autouse=True)
def _no_env_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV, raising=False)


# -- algorithm ---------------------------------------------------------------


def test_pseudonymise_is_keyed_hmac_sha256() -> None:
    expected = hmac.new(SECRET.encode(), ORIGINAL_ID.encode(), hashlib.sha256).hexdigest()
    assert pseudonymise(ORIGINAL_ID, salt=SECRET) == f"DF-{expected[:16].upper()}"


def test_deidentify_dataset_rejects_public_salt(single_dataset: Dataset) -> None:
    with pytest.raises(ValueError, match="public"):
        deidentify_dataset(single_dataset, salt="dicom-forge")


@pytest.mark.parametrize("short", ["", "x", "proj", "fifteen-chars-0"])
def test_deidentify_dataset_rejects_short_secret(single_dataset: Dataset, short: str) -> None:
    if short:  # an empty explicit secret must not silently fall back to another key
        assert len(short) < 16
    with pytest.raises(ValueError, match="at least 16"):
        deidentify_dataset(single_dataset, salt=short)


def test_sixteen_character_secret_accepted(single_dataset: Dataset) -> None:
    result = deidentify_dataset(single_dataset, salt="sixteen-chars-00")
    assert result.pseudonymised_patient_id == pseudonymise(ORIGINAL_ID, salt="sixteen-chars-00")


# -- session secret source ---------------------------------------------------


def test_session_secret_comes_from_csprng(monkeypatch: pytest.MonkeyPatch) -> None:
    """The fallback key must come from the ``secrets`` CSPRNG with 256 bits of entropy."""
    from dicomforge import deidentify

    calls: list[int] = []

    def spy(nbytes: int) -> str:
        calls.append(nbytes)
        return "c" * (2 * nbytes)

    monkeypatch.setattr(deidentify, "_process_secret", None)
    monkeypatch.setattr(deidentify.secrets, "token_hex", spy)
    assert deidentify.resolve_pseudonym_secret() == "c" * 64
    assert calls == [32]


def test_session_secret_is_random_and_full_length(monkeypatch: pytest.MonkeyPatch) -> None:
    from dicomforge import deidentify

    monkeypatch.setattr(deidentify, "_process_secret", None)
    first = deidentify.resolve_pseudonym_secret()
    monkeypatch.setattr(deidentify, "_process_secret", None)
    second = deidentify.resolve_pseudonym_secret()
    assert len(first) == 64 and int(first, 16) >= 0
    assert first != second


# -- secrets never echoed in errors ------------------------------------------

SHORT_CANARY = "SHORT-CANARY-1"  # 14 characters: rejected for length
LEGACY_CANARY = "LEGACY-SALT-CANARY-0123456789"


def echoes(message: str, secret: str, window: int = 6) -> bool:
    """True if any ``window``-length fragment of ``secret`` appears in ``message``.

    Fragments, not just the whole value: pydantic truncates long inputs in error text
    ('LEGAC...0123456789'), which would hide a partial leak from an exact-match check.
    """
    return any(secret[i : i + window] in message for i in range(len(secret) - window + 1))


@pytest.mark.parametrize(
    "data",
    [{"pseudonym_secret": SHORT_CANARY}, {"pseudonym_salt": LEGACY_CANARY}],
    ids=["short-secret", "legacy-salt"],
)
def test_config_errors_do_not_echo_secret(data: dict[str, str]) -> None:
    """Everything that gets displayed or logged (str, repr, traceback) is clean.

    ``ValidationError.errors()`` still returns the caller's own input as structured
    data by pydantic design; code that logs it must pass ``include_input=False``.
    """
    with pytest.raises(ValidationError) as excinfo:
        PipelineConfig.model_validate(data)
    err = excinfo.value
    message = str(err) + repr(err) + "".join(traceback.format_exception(err))
    message += str(err.errors(include_input=False))
    assert not echoes(message, SHORT_CANARY)
    assert not echoes(message, LEGACY_CANARY)


def test_from_json_error_does_not_echo_secret(tmp_path: Path) -> None:
    path = tmp_path / "cfg.json"
    path.write_text(json.dumps({"pseudonym_salt": LEGACY_CANARY}), encoding="utf-8")
    with pytest.raises(ValidationError) as excinfo:
        PipelineConfig.from_json(path)
    assert not echoes("".join(traceback.format_exception(excinfo.value)), LEGACY_CANARY)


def test_short_env_secret_error_does_not_echo_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    from dicomforge.deidentify import resolve_pseudonym_secret

    monkeypatch.setenv(ENV, SHORT_CANARY)
    with pytest.raises(ValueError) as excinfo:
        resolve_pseudonym_secret()
    assert not echoes(str(excinfo.value), SHORT_CANARY)


# -- config policy -----------------------------------------------------------


def test_default_config_does_not_carry_public_salt() -> None:
    assert "dicom-forge" not in PipelineConfig().model_dump_json()


def test_config_rejects_public_salt_as_secret() -> None:
    with pytest.raises(ValidationError, match="public"):
        PipelineConfig(pseudonym_secret="dicom-forge")


def test_config_rejects_short_secret() -> None:
    with pytest.raises(ValidationError, match="at least 16"):
        PipelineConfig(pseudonym_secret="short")


def test_legacy_salt_field_gives_actionable_error() -> None:
    with pytest.raises(ValidationError, match=ENV):
        PipelineConfig.model_validate({"pseudonym_salt": "anything-at-all-here"})


def test_secret_never_serialised(tmp_path: Path) -> None:
    cfg = PipelineConfig(pseudonym_secret=SECRET)
    path = tmp_path / "cfg.json"
    cfg.to_json(path)
    assert SECRET not in path.read_text(encoding="utf-8")
    assert SECRET not in cfg.model_dump_json()
    assert SECRET not in repr(cfg)
    assert SECRET not in str(cfg.model_dump())


# -- pipeline behaviour ------------------------------------------------------


def _pseudonym(src: Path, out: Path, cfg: PipelineConfig | None = None) -> str:
    result = run_pipeline(src, out, config=cfg)
    assert result.deidentification is not None
    pid = result.deidentification.pseudonymised_patient_id
    assert pid is not None
    return pid


@pytest.mark.requires_convert
def test_default_pipeline_pseudonym_not_reversible_with_public_salt(
    synthetic_series: Path, tmp_path: Path
) -> None:
    pid = _pseudonym(synthetic_series, tmp_path / "out")
    assert pid != legacy_public_pseudonym(ORIGINAL_ID)


@pytest.mark.requires_convert
def test_env_secret_gives_stable_pseudonyms(
    synthetic_series: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(ENV, SECRET)
    a = _pseudonym(synthetic_series, tmp_path / "a")
    b = _pseudonym(synthetic_series, tmp_path / "b")
    assert a == b == pseudonymise(ORIGINAL_ID, salt=SECRET)


@pytest.mark.requires_convert
def test_explicit_secret_overrides_env(
    synthetic_series: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(ENV, "environment-secret-should-lose")
    pid = _pseudonym(synthetic_series, tmp_path / "out", PipelineConfig(pseudonym_secret=SECRET))
    assert pid == pseudonymise(ORIGINAL_ID, salt=SECRET)


@pytest.mark.requires_convert
def test_short_env_secret_rejected(
    synthetic_series: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(ENV, "short")
    with pytest.raises(ValueError, match="at least 16"):
        run_pipeline(synthetic_series, tmp_path / "out")


@pytest.mark.requires_convert
def test_missing_secret_warns_without_leaking(
    synthetic_series: Path,
    tmp_path: Path,
    dicomforge_logs: _Capture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dicomforge import deidentify

    # The random fallback key (and its warning) is created once per process.
    monkeypatch.setattr(deidentify, "_process_secret", None)
    _pseudonym(synthetic_series, tmp_path / "out")
    assert deidentify._process_secret is not None
    assert all(deidentify._process_secret not in m for m in dicomforge_logs.messages)
    assert any(ENV in m for m in dicomforge_logs.messages)


@pytest.mark.requires_convert
def test_secret_absent_from_audit_record_and_logs(
    synthetic_series: Path, tmp_path: Path, dicomforge_logs: _Capture
) -> None:
    cfg = PipelineConfig(pseudonym_secret=SECRET)
    result = run_pipeline(synthetic_series, tmp_path / "out", config=cfg)
    assert SECRET not in result.model_dump_json()
    assert all(SECRET not in m for m in dicomforge_logs.messages)


# -- CLI ---------------------------------------------------------------------


@pytest.mark.requires_convert
def test_cli_convert_uses_env_secret(synthetic_series: Path, tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from dicomforge.cli import app

    result = CliRunner().invoke(
        app, ["convert", str(synthetic_series), str(tmp_path / "vol")], env={ENV: SECRET}
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)  # logs go to stderr, so stdout is pure JSON
    assert payload["deidentification"]["pseudonymised_patient_id"] == pseudonymise(
        ORIGINAL_ID, salt=SECRET
    )
    assert SECRET not in result.output
