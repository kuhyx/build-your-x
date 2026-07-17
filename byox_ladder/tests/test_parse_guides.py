"""Unit tests for the guide parser and its difficulty model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from python_pkg.byox_ladder.parse_guides import (
    DEFAULT_EFFORT,
    clean_title,
    lang_effort,
    main,
    parse_guide_line,
    parse_readme,
    split_langs,
)

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

# A tiny README covering a real category, the Uncategorized bucket, a
# before-any-header line, and a non-guide line under a category.
README_SAMPLE = """intro line before any header
#### Build your own `Git`
* [**Go**: _Git in Go_](https://example.com/git)
not a guide line under a category
#### Uncategorized
* [**C++**: _Linux Debugger_](https://example.com/dbg)
"""


def test_split_langs_multiple_separators() -> None:
    assert split_langs("C# / TypeScript & JavaScript") == [
        "C#",
        "TypeScript",
        "JavaScript",
    ]


def test_split_langs_or_separator() -> None:
    assert split_langs("Python or Go") == ["Python", "Go"]


def test_split_langs_empty_falls_back_to_various() -> None:
    assert split_langs("**") == ["Various"]


def test_lang_effort_prefers_easiest_language() -> None:
    assert lang_effort(["C", "Python"]) == 0.3


def test_lang_effort_unknown_language_uses_default() -> None:
    assert lang_effort(["Cobol"]) == DEFAULT_EFFORT


def test_lang_effort_empty_uses_default() -> None:
    assert lang_effort([]) == DEFAULT_EFFORT


def test_clean_title_strips_emphasis() -> None:
    assert clean_title("_Hello World_") == "Hello World"


def test_parse_guide_line_full_record() -> None:
    line = "* [**Go**: _Build X_](https://example.com/x) [video]"
    guide = parse_guide_line(line, "Git")
    assert guide is not None
    assert guide["title"] == "Build X"
    assert guide["langs"] == ["Go"]
    assert guide["category"] == "Git"
    assert guide["tier"] == "beginner"
    assert guide["video"] is True


def test_parse_guide_line_without_language_prefix() -> None:
    guide = parse_guide_line("* [Plain title](https://example.com)", "Git")
    assert guide is not None
    assert guide["langs"] == ["Various"]
    assert guide["title"] == "Plain title"
    assert guide["video"] is False


def test_parse_guide_line_unknown_category_is_unsorted() -> None:
    guide = parse_guide_line("* [**C**: _Thing_](https://example.com)", "Uncategorized")
    assert guide is not None
    assert guide["tier"] == "unsorted"
    assert guide["cat_rank"] == 99


def test_parse_guide_line_non_guide_returns_none() -> None:
    assert parse_guide_line("not a bullet", "Git") is None


def test_parse_readme_groups_and_sorts_by_difficulty() -> None:
    guides = parse_readme(README_SAMPLE)
    titles = [guide["title"] for guide in guides]
    assert "Git in Go" in titles
    assert "Linux Debugger" in titles
    # Git (rank 5) must sort ahead of the Uncategorized bucket (rank 99).
    assert titles.index("Git in Go") < titles.index("Linux Debugger")


def test_parse_readme_ignores_lines_before_any_header() -> None:
    assert parse_readme("* [**Go**: _Orphan_](https://example.com)\n") == []


def test_main_missing_readme_returns_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "python_pkg.byox_ladder.parse_guides.README", tmp_path / "nope.md"
    )
    monkeypatch.setattr(
        "python_pkg.byox_ladder.parse_guides.OUTPUT", tmp_path / "out.json"
    )
    assert main() == 1


def test_main_writes_guides_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    readme = tmp_path / "byox-readme.md"
    readme.write_text(README_SAMPLE, encoding="utf-8")
    output = tmp_path / "guides.json"
    monkeypatch.setattr("python_pkg.byox_ladder.parse_guides.README", readme)
    monkeypatch.setattr("python_pkg.byox_ladder.parse_guides.OUTPUT", output)
    assert main() == 0
    assert output.exists()
