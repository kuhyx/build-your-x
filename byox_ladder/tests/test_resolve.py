"""Unit tests for guide resolution."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from byox_ladder._resolve import (
    GuideResolutionError,
    _slug,
    load_guides,
    resolve,
)

if TYPE_CHECKING:
    from pathlib import Path

GUIDES = [
    {"title": "Create a CLI tool in Javascript", "url": "https://x/create-cli-tool"},
    {"title": "Build a database", "url": "https://x/build-db"},
    {"title": "Another CLI thing", "url": "https://y/cli-extra"},
    {"title": "Red widget", "url": "https://x/red"},
    {"title": "Blue widget", "url": "https://x/blue"},
]


def test_load_guides_reads_json(tmp_path: Path) -> None:
    path = tmp_path / "guides.json"
    path.write_text('[{"title": "A", "url": "u"}]', encoding="utf-8")
    assert load_guides(path) == [{"title": "A", "url": "u"}]


def test_load_guides_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(GuideResolutionError, match="make build"):
        load_guides(tmp_path / "nope.json")


def test_slug_strips_trailing_slash() -> None:
    assert _slug("https://x/some-guide/") == "some-guide"


def test_resolve_empty_token_raises() -> None:
    with pytest.raises(GuideResolutionError, match="empty"):
        resolve("   ", GUIDES)


def test_resolve_exact_url() -> None:
    assert resolve("https://x/build-db", GUIDES)["title"] == "Build a database"


def test_resolve_url_substring_unique() -> None:
    assert resolve("cli-tool", GUIDES)["title"] == "Create a CLI tool in Javascript"


def test_resolve_slug_match() -> None:
    assert resolve("build-db", GUIDES)["title"] == "Build a database"


def test_resolve_title_substring_unique() -> None:
    assert resolve("database", GUIDES)["url"] == "https://x/build-db"


def test_resolve_ambiguous_url_lists_candidates() -> None:
    with pytest.raises(GuideResolutionError) as excinfo:
        resolve("cli", GUIDES)
    assert len(excinfo.value.candidates) == 2


def test_resolve_ambiguous_title_lists_candidates() -> None:
    with pytest.raises(GuideResolutionError) as excinfo:
        resolve("widget", GUIDES)
    assert len(excinfo.value.candidates) == 2


def test_resolve_not_found() -> None:
    with pytest.raises(GuideResolutionError, match="no guide matches"):
        resolve("zzznope", GUIDES)
