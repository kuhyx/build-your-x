"""Unit tests for the local progress store."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from byox_ladder import _progress
from byox_ladder._progress import (
    ProgressEntry,
    default_progress_path,
    load_progress,
    mark,
    now_ms,
    save_progress,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_default_progress_path_uses_xdg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", "/data")
    assert default_progress_path().as_posix() == "/data/byox_ladder/progress.json"


def test_default_progress_path_falls_back_home(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    path = default_progress_path()
    assert path.name == "progress.json"
    assert path.parent.name == "byox_ladder"
    assert ".local/share" in path.as_posix()


def test_now_ms_is_int() -> None:
    assert isinstance(now_ms(), int)


def test_load_missing_file_is_empty(tmp_path: Path) -> None:
    assert load_progress(tmp_path / "nope.json") == {}


def test_load_corrupt_file_is_empty(tmp_path: Path) -> None:
    path = tmp_path / "progress.json"
    path.write_text("not json", encoding="utf-8")
    assert load_progress(path) == {}


def test_load_parses_entries_with_defaults(tmp_path: Path) -> None:
    path = tmp_path / "progress.json"
    path.write_text('{"u1": {"done": true}, "u2": {}}', encoding="utf-8")
    progress = load_progress(path)
    assert progress["u1"] == ProgressEntry("u1", done=True, note="", updated_ms=0)
    assert progress["u2"] == ProgressEntry("u2", done=False, note="", updated_ms=0)


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "sub" / "progress.json"  # parent created on save
    progress = {"u1": ProgressEntry("u1", done=True, note="builds/x", updated_ms=7)}
    save_progress(path, progress)
    assert load_progress(path) == progress


def test_save_cleans_temp_on_replace_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "progress.json"

    def _boom(_self: object, _target: object) -> None:
        message = "replace failed"
        raise OSError(message)

    monkeypatch.setattr(_progress.Path, "replace", _boom)
    with pytest.raises(OSError, match="replace failed"):
        save_progress(path, {})
    # No stray *.tmp files left behind.
    assert list(tmp_path.glob("*.tmp")) == []


def test_mark_creates_new_entry(tmp_path: Path) -> None:
    progress: dict[str, ProgressEntry] = {}
    entry = mark(progress, "u1", done=True, note="n", when_ms=42)
    assert entry == ProgressEntry("u1", done=True, note="n", updated_ms=42)
    assert progress["u1"] is entry


def test_mark_updates_only_given_fields() -> None:
    progress = {"u1": ProgressEntry("u1", done=True, note="keep", updated_ms=1)}
    mark(progress, "u1", done=False, when_ms=9)
    assert progress["u1"] == ProgressEntry("u1", done=False, note="keep", updated_ms=9)


def test_mark_defaults_timestamp_to_now(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_progress, "now_ms", lambda: 12345)
    progress: dict[str, ProgressEntry] = {}
    entry = mark(progress, "u1", note="n")
    assert entry.updated_ms == 12345
    assert entry.done is False
