"""Resolve a user-typed token to exactly one guide from ``guides.json``.

The CLI lets you name a guide loosely — a full URL, a url-slug fragment, or a
words from the title. This module turns that token into a single guide record,
or reports the ambiguity/absence with the candidate list so the user can refine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
# Same derived dataset build_pages.py consumes.
GUIDES_JSON = HERE / "guides.json"

# A guide record as parsed by parse_guides.py (title, url, tier, ...).
Guide = dict[str, Any]


class GuideResolutionError(Exception):
    """Raised when a token matches zero or several guides.

    Attributes:
        candidates: The guides that matched (empty when nothing matched); the
            CLI prints these so the user can pick a more specific token.
    """

    def __init__(self, message: str, candidates: list[Guide]) -> None:
        """Store the human message and the ambiguous/empty candidate list."""
        super().__init__(message)
        self.candidates = candidates


def load_guides(path: Path = GUIDES_JSON) -> list[Guide]:
    """Load the parsed guide list.

    Args:
        path: Location of ``guides.json``.

    Returns:
        The list of guide records.

    Raises:
        GuideResolutionError: If the dataset is missing (needs ``make build``).
    """
    try:
        data: list[Guide] = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        message = f"missing {path} — run `make build` (or parse_guides.py) first"
        raise GuideResolutionError(message, []) from exc
    return data


def _slug(url: str) -> str:
    """Return the last non-empty path segment of a URL, lowercased."""
    return url.rstrip("/").rsplit("/", 1)[-1].lower()


def _pick(matches: list[Guide], token: str) -> Guide | None:
    """Return the sole match, ``None`` for no match, or raise if ambiguous.

    Args:
        matches: Guides that matched at one specificity level.
        token: The original query, for the error message.

    Returns:
        The single matching guide, or ``None`` when ``matches`` is empty.

    Raises:
        GuideResolutionError: If more than one guide matched.
    """
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        message = f"{token!r} is ambiguous — {len(matches)} guides match"
        raise GuideResolutionError(message, matches)
    return None


def resolve(token: str, guides: list[Guide]) -> Guide:
    """Resolve ``token`` to exactly one guide.

    Resolution tries, in order of specificity: an exact URL, a URL/slug
    substring, then a title substring. The first level that yields matches
    decides the outcome — one match wins; several at that level is an ambiguity
    error rather than silently widening the search.

    Args:
        token: The user's query (URL, slug fragment, or title words).
        guides: The guide list to search.

    Returns:
        The matching guide record.

    Raises:
        GuideResolutionError: If the token is empty, matches nothing, or is
            ambiguous at its most specific matching level.
    """
    query = token.strip()
    if not query:
        empty = "empty guide query"
        raise GuideResolutionError(empty, [])
    lowered = query.lower()

    for guide in guides:
        if guide["url"] == query:
            return guide

    url_matches = [
        g for g in guides if lowered in g["url"].lower() or lowered in _slug(g["url"])
    ]
    picked = _pick(url_matches, query)
    if picked is not None:
        return picked

    title_matches = [g for g in guides if lowered in g["title"].lower()]
    picked = _pick(title_matches, query)
    if picked is not None:
        return picked

    missing = f"no guide matches {query!r}"
    raise GuideResolutionError(missing, [])
