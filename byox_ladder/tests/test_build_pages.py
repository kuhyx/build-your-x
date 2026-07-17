"""Unit tests for the standalone page builder."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from byox_ladder.build_pages import (
    _inline,
    _progress_payload,
    build_category_page,
    build_guide_page,
    main,
    standalone,
)

if TYPE_CHECKING:
    from pathlib import Path

# A template containing both injection markers.
TEMPLATE = "<title>x</title><script>/*__GUIDES__*/\n/*__PROGRESS__*/</script>"


def _write(dirpath: Path, name: str, body: str) -> None:
    (dirpath / name).write_text(body, encoding="utf-8")


def _setup_guides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, template: str, guides: str
) -> Path:
    """Point build_pages at a temp template/guides pair and empty progress."""
    templates = tmp_path / "templates"
    templates.mkdir(exist_ok=True)
    _write(templates, "guide.template.html", template)
    guides_json = tmp_path / "guides.json"
    guides_json.write_text(guides, encoding="utf-8")
    monkeypatch.setattr("byox_ladder.build_pages.TEMPLATES", templates)
    monkeypatch.setattr("byox_ladder.build_pages.GUIDES_JSON", guides_json)
    monkeypatch.setattr(
        "byox_ladder.build_pages.PROGRESS_PATH", tmp_path / "progress.json"
    )
    return templates


def test_standalone_wraps_content() -> None:
    out = standalone("<p>hi</p>")
    assert out.startswith("<!doctype html>")
    assert "<p>hi</p>" in out
    assert out.rstrip().endswith("</html>")


def test_inline_escapes_closing_script() -> None:
    assert _inline({"a": "</script>"}) == '{"a":"<\\/script>"}'


def test_build_guide_page_injects_guides_and_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup_guides(tmp_path, monkeypatch, TEMPLATE, '[{"title": "A"}]')
    html = build_guide_page()
    assert "const GUIDES = [" in html
    assert "const PROGRESS = {" in html
    assert html.startswith("<!doctype html>")


def test_build_guide_page_bakes_done_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    progress = tmp_path / "progress.json"
    progress.write_text(
        '{"u1": {"done": true, "note": "builds/x", "updated_ms": 5},'
        ' "u2": {"done": false, "note": "", "updated_ms": 3}}',
        encoding="utf-8",
    )
    _setup_guides(tmp_path, monkeypatch, TEMPLATE, "[]")
    monkeypatch.setattr("byox_ladder.build_pages.PROGRESS_PATH", progress)
    html = build_guide_page()
    # Only the done guide is inlined.
    assert '"u1":{"done":true,"note":"builds/x"}' in html
    assert "u2" not in html


def test_build_guide_page_missing_guides_marker_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup_guides(tmp_path, monkeypatch, "<title>no marker</title>", "[]")
    with pytest.raises(ValueError, match="__GUIDES__"):
        build_guide_page()


def test_build_guide_page_missing_progress_marker_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup_guides(tmp_path, monkeypatch, "<script>/*__GUIDES__*/</script>", "[]")
    with pytest.raises(ValueError, match="__PROGRESS__"):
        build_guide_page()


def test_progress_payload_filters_and_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    progress = tmp_path / "progress.json"
    progress.write_text(
        '{"a": {"done": true, "note": "n", "updated_ms": 1},'
        ' "b": {"done": false, "note": "", "updated_ms": 2}}',
        encoding="utf-8",
    )
    monkeypatch.setattr("byox_ladder.build_pages.PROGRESS_PATH", progress)
    assert _progress_payload() == {"a": {"done": True, "note": "n"}}


def test_build_category_page_wraps_template(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    templates = tmp_path / "templates"
    templates.mkdir()
    _write(templates, "category.html", "<title>cat</title>")
    monkeypatch.setattr("byox_ladder.build_pages.TEMPLATES", templates)
    html = build_category_page()
    assert "<title>cat</title>" in html
    assert html.startswith("<!doctype html>")


def test_main_missing_guides_returns_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("byox_ladder.build_pages.GUIDES_JSON", tmp_path / "nope.json")
    assert main() == 1


def test_main_writes_both_pages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    templates = _setup_guides(tmp_path, monkeypatch, TEMPLATE, "[]")
    _write(templates, "category.html", "<title>cat</title>")
    monkeypatch.setattr("byox_ladder.build_pages.HERE", tmp_path)
    assert main() == 0
    assert (tmp_path / "guide-ladder.html").exists()
    assert (tmp_path / "category-ladder.html").exists()
