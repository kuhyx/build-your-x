"""Unit tests for crdt_sync integration (no real network)."""

from __future__ import annotations

import socket
from typing import TYPE_CHECKING

from crdt_sync import GitHubSyncError, Hlc, Record

from byox_ladder import _sync
from byox_ladder._progress import ProgressEntry, load_progress
from byox_ladder._sync import (
    _decode,
    _encode,
    device_id,
    log_to_progress,
    progress_to_log,
    read_token,
    run_sync,
)

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _token(tmp_path: Path) -> Path:
    path = tmp_path / "sync_token"
    path.write_text("ghp_faketoken\n", encoding="utf-8")
    return path


def test_device_id_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BYOX_DEVICE_ID", "laptop")
    assert device_id() == "laptop"


def test_device_id_hostname_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BYOX_DEVICE_ID", raising=False)
    monkeypatch.setattr(socket, "gethostname", lambda: "myhost")
    assert device_id() == "myhost"


def test_read_token_missing(tmp_path: Path) -> None:
    assert read_token(tmp_path / "nope") is None


def test_read_token_empty(tmp_path: Path) -> None:
    path = tmp_path / "tok"
    path.write_text("   \n", encoding="utf-8")
    assert read_token(path) is None


def test_read_token_value(tmp_path: Path) -> None:
    assert read_token(_token(tmp_path)) == "ghp_faketoken"


def test_progress_to_log_builds_records() -> None:
    progress = {"u1": ProgressEntry("u1", done=True, note="n", updated_ms=5)}
    log = progress_to_log(progress, "pc")
    assert log["u1"].fields["done"][0] is True
    assert log["u1"].fields["note"][0] == "n"
    assert log["u1"].fields["done"][1].wall_time_ms == 5


def test_log_to_progress_round_trip() -> None:
    progress = {"u1": ProgressEntry("u1", done=True, note="n", updated_ms=5)}
    assert log_to_progress(progress_to_log(progress, "pc")) == progress


def test_encode_decode_round_trip() -> None:
    log = progress_to_log(
        {"u1": ProgressEntry("u1", done=True, note="n", updated_ms=5)}, "pc"
    )
    restored = _decode(_encode(log))
    assert restored["u1"].fields["done"][0] is True
    assert restored["u1"].fields["note"][0] == "n"


def test_log_to_progress_skips_deleted() -> None:
    hlc = Hlc.new_tick("pc", wall_time_ms=1)
    log = {"u1": Record(id="u1", fields={"done": (True, hlc)}, deleted=True)}
    assert log_to_progress(log) == {}


def test_log_to_progress_missing_fields_default() -> None:
    log = {"u1": Record(id="u1", fields={})}
    assert log_to_progress(log) == {
        "u1": ProgressEntry("u1", done=False, note="", updated_ms=0)
    }


def test_run_sync_unconfigured(tmp_path: Path) -> None:
    outcome = run_sync(
        progress_path=tmp_path / "p.json", token_file=tmp_path / "no_token"
    )
    assert outcome.status == "unconfigured"


def test_run_sync_ok_writes_merged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    progress_path = tmp_path / "p.json"
    merged = progress_to_log(
        {"u1": ProgressEntry("u1", done=True, note="n", updated_ms=5)}, "pc"
    )
    monkeypatch.setattr(_sync, "GitHubSyncClient", lambda *a, **k: object())
    monkeypatch.setattr(_sync, "sync_log", lambda **_k: merged)
    outcome = run_sync(progress_path=progress_path, token_file=_token(tmp_path))
    assert outcome.status == "ok"
    assert (outcome.total, outcome.done) == (1, 1)
    assert load_progress(progress_path)["u1"].done is True


def test_run_sync_error_is_caught(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(**_kwargs: object) -> None:
        message = "nope"
        raise GitHubSyncError(message)

    monkeypatch.setattr(_sync, "GitHubSyncClient", lambda *a, **k: object())
    monkeypatch.setattr(_sync, "sync_log", _boom)
    outcome = run_sync(progress_path=tmp_path / "p.json", token_file=_token(tmp_path))
    assert outcome.status == "error"
    assert outcome.detail == "nope"
