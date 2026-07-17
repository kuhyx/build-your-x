#!/usr/bin/env python3
"""Parse the build-your-own-x README into a ranked, tiered list of guides.

Reads a local copy of the upstream README (``byox-readme.md`` — fetch it with the
command documented in this folder's ``README.md``, or run ``make build``) and
writes ``guides.json``.

Difficulty model: every guide inherits its category's tier — the dominant
signal — while its language only nudges the ordering *within* that tier
(lower-level languages such as C or Rust sort a little harder than Python or
JavaScript). See ``README.md`` for the full rationale.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import re

logger = logging.getLogger(__name__)

HERE = Path(__file__).resolve().parent
README = HERE / "byox-readme.md"
OUTPUT = HERE / "guides.json"

# Category display name -> (global difficulty rank 1..30, tier). The rank order
# mirrors the approved per-category ladder; keys match the exact backtick names
# used in the README headers.
CATEGORIES: dict[str, tuple[int, str]] = {
    "Command-Line Tool": (1, "beginner"),
    "Bot": (2, "beginner"),
    "Template Engine": (3, "beginner"),
    "Text Editor": (4, "beginner"),
    "Git": (5, "beginner"),
    "Shell": (6, "intermediate"),
    "Web Server": (7, "intermediate"),
    "Search Engine": (8, "intermediate"),
    "BitTorrent Client": (9, "intermediate"),
    "Front-end Framework / Library": (10, "intermediate"),
    "Regex Engine": (11, "intermediate"),
    "Game": (12, "intermediate"),
    "Programming Language": (13, "advanced"),
    "Emulator / Virtual Machine": (14, "advanced"),
    "Neural Network": (15, "advanced"),
    "Memory Allocator": (16, "advanced"),
    "Blockchain / Cryptocurrency": (17, "advanced"),
    "Database": (18, "advanced"),
    "3D Renderer": (19, "advanced"),
    "Physics Engine": (20, "advanced"),
    "Docker": (21, "advanced"),
    "Voxel Engine": (22, "advanced"),
    "Network Stack": (23, "expert"),
    "AI Model": (24, "expert"),
    "Visual Recognition System": (25, "expert"),
    "Augmented Reality": (26, "expert"),
    "Web Browser": (27, "expert"),
    "Processor": (28, "expert"),
    "Operating System": (29, "expert"),
    "Distributed Systems": (30, "expert"),
}

# Rank used for the repo's "Uncategorized" bucket, sorted after every real tier.
UNSORTED_RANK = 99

# Per-language ordering nudge (0.0 = high-level, higher = lower-level / more
# effort). Only orders guides *within* a category; it never crosses a tier.
LANG_EFFORT: dict[str, float] = {
    "assembly": 0.9,
    "asm": 0.9,
    "c": 0.8,
    "c++": 0.8,
    "cpp": 0.8,
    "rust": 0.75,
    "zig": 0.75,
    "d": 0.7,
    "nim": 0.6,
    "haskell": 0.6,
    "ocaml": 0.6,
    "go": 0.55,
    "scala": 0.55,
    "c#": 0.5,
    "java": 0.5,
    "kotlin": 0.5,
    "swift": 0.5,
    "f#": 0.5,
    "clojure": 0.45,
    "elixir": 0.4,
    "shell": 0.4,
    "bash": 0.4,
    "r": 0.4,
    "typescript": 0.35,
    "php": 0.35,
    "perl": 0.35,
    "dart": 0.35,
    "javascript": 0.3,
    "node.js": 0.3,
    "node": 0.3,
    "ruby": 0.3,
    "python": 0.3,
    "lua": 0.3,
    "any": 0.25,
    "pseudocode": 0.2,
}

# Default nudge for a language not present in ``LANG_EFFORT``.
DEFAULT_EFFORT = 0.5

HEADER_RE = re.compile(r"^####\s+Build your own\s+`([^`]+)`")
UNCAT_RE = re.compile(r"^####\s+Uncategorized")
GUIDE_RE = re.compile(r"^\*\s+\[(.+)\]\((\S+?)\)(.*)$")
LABEL_RE = re.compile(r"^\*\*(.+?)\*\*:\s*(.*)$")


def split_langs(raw: str) -> list[str]:
    """Split a ``C# / TypeScript`` language blob into a clean list of names."""
    parts = re.split(r"[/,&]| or ", raw)
    names = [part.strip().strip("*").strip() for part in parts]
    cleaned = [name for name in names if name]
    return cleaned or ["Various"]


def lang_effort(langs: list[str]) -> float:
    """Return the easiest listed language's nudge (you pick your best one)."""
    values = [LANG_EFFORT.get(lang.lower(), DEFAULT_EFFORT) for lang in langs]
    return min(values) if values else DEFAULT_EFFORT


def clean_title(rest: str) -> str:
    """Strip surrounding markdown italics/emphasis from a guide title."""
    title = rest.strip()
    title = re.sub(r"^_+", "", title)
    title = re.sub(r"_+$", "", title)
    return title.strip().strip("*").strip()


def parse_guide_line(line: str, category: str) -> dict[str, object] | None:
    """Parse one ``* [**Lang**: _Title_](url)`` line into a guide record."""
    match = GUIDE_RE.match(line.strip())
    if match is None:
        return None
    label, url, trailer = match.group(1), match.group(2), match.group(3)
    label_match = LABEL_RE.match(label)
    if label_match is not None:
        langs = split_langs(label_match.group(1))
        title = clean_title(label_match.group(2))
    else:
        langs = ["Various"]
        title = clean_title(label)
    rank, tier = CATEGORIES.get(category, (UNSORTED_RANK, "unsorted"))
    return {
        "title": title,
        "url": url,
        "langs": langs,
        "category": category,
        "cat_rank": rank,
        "tier": tier,
        "video": "[video]" in trailer.lower(),
        "score": round(rank * 10 + lang_effort(langs), 2),
    }


def parse_readme(text: str) -> list[dict[str, object]]:
    """Parse the whole README text into a score-sorted list of guides."""
    guides: list[dict[str, object]] = []
    current: str | None = None
    for line in text.splitlines():
        header = HEADER_RE.match(line)
        if header is not None:
            current = header.group(1).strip()
            continue
        if UNCAT_RE.match(line):
            current = "Uncategorized"
            continue
        if current is None:
            continue
        guide = parse_guide_line(line, current)
        if guide is not None:
            guides.append(guide)
    guides.sort(key=lambda item: (item["score"], str(item["title"]).lower()))
    return guides


def main() -> int:
    """Parse ``byox-readme.md`` and write ``guides.json``; return an exit code."""
    if not README.exists():
        logger.error("missing %s — fetch it first (see README.md / make build)", README)
        return 1
    guides = parse_readme(README.read_text(encoding="utf-8"))
    OUTPUT.write_text(json.dumps(guides, indent=1), encoding="utf-8")
    logger.info("wrote %s (%d guides)", OUTPUT.name, len(guides))
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    raise SystemExit(main())
