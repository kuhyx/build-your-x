"""Unit tests for the standalone page builder."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from python_pkg.byox_ladder.build_pages import (
    build_category_page,
    build_guide_page,
    main,
    standalone,
)

if TYPE_CHECKING:
    from pathlib import Path


def _write(dirpath: Path, name: str, body: str) -> None:
    (dirpath / name).write_text(body, encoding="utf-8")


def test_standalone_wraps_content() -> None:
    out = standalone("<p>hi</p>")
    assert out.startswith("<!doctype html>")
    assert "<p>hi</p>" in out
    assert out.rstrip().endswith("</html>")


def test_build_guide_page_injects_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    templates = tmp_path / "templates"
    templates.mkdir()
    _write(
        templates,
        "guide.template.html",
        "<title>x</title><script>/*__GUIDES__*/</script>",
    )
    guides_json = tmp_path / "guides.json"
    guides_json.write_text('[{"title": "A"}]', encoding="utf-8")
    monkeypatch.setattr("python_pkg.byox_ladder.build_pages.TEMPLATES", templates)
    monkeypatch.setattr("python_pkg.byox_ladder.build_pages.GUIDES_JSON", guides_json)
    html = build_guide_page()
    assert "const GUIDES = [" in html
    assert html.startswith("<!doctype html>")


def test_build_guide_page_missing_marker_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    templates = tmp_path / "templates"
    templates.mkdir()
    _write(templates, "guide.template.html", "<title>no marker</title>")
    guides_json = tmp_path / "guides.json"
    guides_json.write_text("[]", encoding="utf-8")
    monkeypatch.setattr("python_pkg.byox_ladder.build_pages.TEMPLATES", templates)
    monkeypatch.setattr("python_pkg.byox_ladder.build_pages.GUIDES_JSON", guides_json)
    with pytest.raises(ValueError, match="marker"):
        build_guide_page()


def test_build_category_page_wraps_template(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    templates = tmp_path / "templates"
    templates.mkdir()
    _write(templates, "category.html", "<title>cat</title>")
    monkeypatch.setattr("python_pkg.byox_ladder.build_pages.TEMPLATES", templates)
    html = build_category_page()
    assert "<title>cat</title>" in html
    assert html.startswith("<!doctype html>")


def test_main_missing_guides_returns_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "python_pkg.byox_ladder.build_pages.GUIDES_JSON", tmp_path / "nope.json"
    )
    assert main() == 1


def test_main_writes_both_pages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    templates = tmp_path / "templates"
    templates.mkdir()
    _write(templates, "guide.template.html", "<script>/*__GUIDES__*/</script>")
    _write(templates, "category.html", "<title>cat</title>")
    guides_json = tmp_path / "guides.json"
    guides_json.write_text("[]", encoding="utf-8")
    monkeypatch.setattr("python_pkg.byox_ladder.build_pages.TEMPLATES", templates)
    monkeypatch.setattr("python_pkg.byox_ladder.build_pages.GUIDES_JSON", guides_json)
    monkeypatch.setattr("python_pkg.byox_ladder.build_pages.HERE", tmp_path)
    assert main() == 0
    assert (tmp_path / "guide-ladder.html").exists()
    assert (tmp_path / "category-ladder.html").exists()
