"""Unit tests for the byox CLI."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from byox_ladder import _cli
from byox_ladder._progress import load_progress
from byox_ladder._sync import SyncOutcome

if TYPE_CHECKING:
    from pathlib import Path

GUIDES = [
    {"title": "CLI tool", "url": "https://x/cli-tool", "tier": "beginner"},
    {"title": "A database", "url": "https://x/build-db", "tier": "advanced"},
]


@pytest.fixture
def progress_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect the CLI's guide list and progress store to test doubles."""
    path = tmp_path / "progress.json"
    monkeypatch.setattr(_cli, "load_guides", lambda: GUIDES)
    monkeypatch.setattr(_cli, "PROGRESS_PATH", path)
    return path


def test_done_marks_and_reports(
    progress_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _cli.main(["done", "cli-tool", "--note", "builds/x"]) == 0
    out = capsys.readouterr().out
    assert "CLI tool" in out
    assert "(1/2)" in out
    entry = load_progress(progress_file)["https://x/cli-tool"]
    assert entry.done is True
    assert entry.note == "builds/x"


def test_undone_clears(progress_file: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _cli.main(["done", "cli-tool"])
    capsys.readouterr()
    assert _cli.main(["undone", "cli-tool"]) == 0
    assert "○" in capsys.readouterr().out
    assert load_progress(progress_file)["https://x/cli-tool"].done is False


def test_note_sets_text(
    progress_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _cli.main(["note", "cli-tool", "see builds/x"]) == 0
    assert "noted" in capsys.readouterr().out
    assert load_progress(progress_file)["https://x/cli-tool"].note == "see builds/x"


def test_status_empty(progress_file: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert _cli.main(["status"]) == 0
    out = capsys.readouterr().out
    assert "0/2 guides done" in out
    assert "beginner" in out
    assert "Done:" not in out


def test_status_lists_done_with_note(
    progress_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _cli.main(["done", "cli-tool", "--note", "builds/x"])
    capsys.readouterr()
    assert _cli.main(["status"]) == 0
    out = capsys.readouterr().out
    assert "1/2 guides done" in out
    assert "Done:" in out
    assert "builds/x" in out


def test_build_delegates(progress_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_cli.build_pages, "main", lambda: 0)
    assert _cli.main(["build"]) == 0


@pytest.mark.parametrize(
    ("outcome", "code", "needle"),
    [
        (SyncOutcome("ok", 2, 1, ""), 0, "synced: 1/2"),
        (SyncOutcome("unconfigured", 0, 0, "/tok"), 0, "sync skipped"),
        (SyncOutcome("error", 0, 0, "boom"), 1, "sync failed: boom"),
    ],
)
def test_sync_reports_outcome(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    outcome: SyncOutcome,
    code: int,
    needle: str,
) -> None:
    monkeypatch.setattr(_cli, "run_sync", lambda: outcome)
    assert _cli.main(["sync"]) == code
    assert needle in capsys.readouterr().out


def test_unknown_guide_errors(
    progress_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _cli.main(["done", "zzznope"]) == 1
    assert "error:" in capsys.readouterr().out


def test_ambiguous_guide_lists_candidates(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    guides: list[dict[str, Any]] = [
        {"title": "Red widget", "url": "https://x/red", "tier": "beginner"},
        {"title": "Blue widget", "url": "https://x/blue", "tier": "beginner"},
    ]
    monkeypatch.setattr(_cli, "load_guides", lambda: guides)
    assert _cli.main(["done", "widget"]) == 1
    out = capsys.readouterr().out
    assert "https://x/red" in out
    assert "https://x/blue" in out
