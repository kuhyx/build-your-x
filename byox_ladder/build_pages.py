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

logger = logging.getLogger(__name__)

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE / "templates"
GUIDES_JSON = HERE / "guides.json"

# Placeholder in the guide template that the inlined dataset replaces.
MARKER = "/*__GUIDES__*/"

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


def build_guide_page() -> str:
    """Inject ``guides.json`` into the guide template; return standalone HTML."""
    guides = json.loads(GUIDES_JSON.read_text(encoding="utf-8"))
    # Compact payload; guard any "</" so inline data can't close the script tag.
    payload = json.dumps(guides, separators=(",", ":")).replace("</", "<\\/")
    template = (TEMPLATES / "guide.template.html").read_text(encoding="utf-8")
    if MARKER not in template:
        message = f"marker {MARKER!r} not found in guide template"
        raise ValueError(message)
    return standalone(template.replace(MARKER, f"const GUIDES = {payload};"))


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
