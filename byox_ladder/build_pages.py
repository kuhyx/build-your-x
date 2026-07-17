#!/usr/bin/env python3
"""Build the standalone HTML ladder pages from templates and parsed guide data.

Produces two self-contained, dependency-free pages next to this script:

* ``guide-ladder.html`` — every individual guide, built by injecting
  ``guides.json`` (written by ``parse_guides.py``) into the guide template.
* ``category-ladder.html`` — the 30-category ladder, a static template.

Both are wrapped in a minimal HTML document skeleton so they open directly via
``file://`` with no server, fonts, or network access. Run ``make build`` to
regenerate the whole pipeline.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from byox_ladder._progress import PROGRESS_PATH, load_progress

logger = logging.getLogger(__name__)

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE / "templates"
GUIDES_JSON = HERE / "guides.json"

# Placeholders in the guide template that the inlined datasets replace.
MARKER = "/*__GUIDES__*/"
PROGRESS_MARKER = "/*__PROGRESS__*/"

# Minimal, valid document skeleton added around the published page content
# (claude.ai injects an equivalent wrapper; local files need their own).
SKELETON_HEAD = (
    "<!doctype html>\n"
    '<html lang="en">\n'
    "<head>\n"
    '<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
)
SKELETON_TAIL = "\n</html>\n"


def standalone(content: str) -> str:
    """Wrap page content in a minimal HTML document skeleton."""
    return SKELETON_HEAD + content + SKELETON_TAIL


def _progress_payload() -> dict[str, dict[str, object]]:
    """Return ``{url: {done, note}}`` for every completed guide.

    Reads the local (crdt_sync-backed) progress store. Only done guides are
    inlined — the dashboard shows a note solely for completed guides, so
    carrying not-done entries would just bloat the page.
    """
    progress = load_progress(PROGRESS_PATH)
    return {
        url: {"done": entry.done, "note": entry.note}
        for url, entry in progress.items()
        if entry.done
    }


def _inline(payload: object) -> str:
    """Serialize ``payload`` compactly, guarding ``</`` from closing the script."""
    return json.dumps(payload, separators=(",", ":")).replace("</", "<\\/")


def build_guide_page() -> str:
    """Inject guides + progress into the guide template; return standalone HTML."""
    guides = json.loads(GUIDES_JSON.read_text(encoding="utf-8"))
    template = (TEMPLATES / "guide.template.html").read_text(encoding="utf-8")
    for marker in (MARKER, PROGRESS_MARKER):
        if marker not in template:
            message = f"marker {marker!r} not found in guide template"
            raise ValueError(message)
    page = template.replace(MARKER, f"const GUIDES = {_inline(guides)};")
    page = page.replace(
        PROGRESS_MARKER, f"const PROGRESS = {_inline(_progress_payload())};"
    )
    return standalone(page)


def build_category_page() -> str:
    """Return the standalone category ladder (static content, no data)."""
    content = (TEMPLATES / "category.html").read_text(encoding="utf-8")
    return standalone(content)


def main() -> int:
    """Write both standalone ladder pages next to this script; return an exit code."""
    if not GUIDES_JSON.exists():
        logger.error(
            "missing %s — run parse_guides.py first (or make build)", GUIDES_JSON
        )
        return 1
    (HERE / "guide-ladder.html").write_text(build_guide_page(), encoding="utf-8")
    (HERE / "category-ladder.html").write_text(build_category_page(), encoding="utf-8")
    logger.info("wrote guide-ladder.html and category-ladder.html")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    raise SystemExit(main())
