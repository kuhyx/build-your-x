"""Local progress store for the build-your-own-x tracker.

A progress entry records, per guide, whether it is done and a freeform note
(typically the path to where you built it). Entries are keyed by the guide's
**URL** — the only stable identifier, since :func:`byox_ladder.parse_guides`
re-sorts guides by ``(score, title)`` on every rebuild, so title and list index
are not stable keys.

The on-disk format is a plain JSON object ``{url: {done, note, updated_ms}}``,
deliberately simple so :mod:`byox_ladder._sync` can adapt it to and from
crdt_sync ``Record``s. ``updated_ms`` seeds the hybrid-logical-clock timestamp
used for last-writer-wins merges across devices.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import os
from pathlib import Path
import tempfile
import time

logger = logging.getLogger(__name__)


@dataclass
class ProgressEntry:
    """One guide's tracked state.

    Attributes:
        url: The guide URL; also the store key and cross-device record id.
        done: Whether the guide has been completed.
        note: Freeform note, usually the build location (e.g. a repo path).
        updated_ms: Last modification time in Unix milliseconds; used to order
            merges when the same guide is edited on more than one device.
    """

    url: str
    done: bool
    note: str
    updated_ms: int


# Store type: guide URL -> its tracked state.
Progress = dict[str, ProgressEntry]


def default_progress_path() -> Path:
    """Return the XDG data path for the progress store.

    Returns:
        ``$XDG_DATA_HOME/byox_ladder/progress.json`` (falling back to
        ``~/.local/share`` when the variable is unset), matching where kuhy's
        other synced tools keep per-device state.
    """
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base / "byox_ladder" / "progress.json"


# Module-level default so callers (and tests) can monkeypatch a single location,
# mirroring build_pages.GUIDES_JSON.
PROGRESS_PATH = default_progress_path()


def now_ms() -> int:
    """Return the current time in Unix milliseconds."""
    return int(time.time() * 1000)


def load_progress(path: Path) -> Progress:
    """Load the progress store, tolerating a missing or corrupt file.

    A missing file (fresh install) or unreadable/malformed JSON both yield an
    empty store rather than raising — losing local progress must never crash the
    CLI, and the synced copy can repopulate it.

    Args:
        path: Location of the progress JSON file.

    Returns:
        A mapping of guide URL to :class:`ProgressEntry` (empty if absent).
    """
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError):
        logger.warning("could not read progress at %s; starting empty", path)
        return {}
    progress: Progress = {}
    for url, entry in raw.items():
        progress[url] = ProgressEntry(
            url=url,
            done=bool(entry.get("done", False)),
            note=str(entry.get("note", "")),
            updated_ms=int(entry.get("updated_ms", 0)),
        )
    return progress


def save_progress(path: Path, progress: Progress) -> None:
    """Atomically write the progress store to ``path``.

    Writes to a temporary file in the same directory and renames it into place
    so a crash mid-write can never truncate the store (mirrors crdt_sync's own
    temp-then-rename persistence).

    Args:
        path: Destination JSON file.
        progress: The store to serialize.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        url: {"done": e.done, "note": e.note, "updated_ms": e.updated_ms}
        for url, e in progress.items()
    }
    text = json.dumps(payload, indent=1, sort_keys=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        tmp.replace(path)
    finally:
        # Clean up the temp file if the rename never happened.
        if tmp.exists():
            tmp.unlink()


def mark(
    progress: Progress,
    url: str,
    *,
    done: bool | None = None,
    note: str | None = None,
    when_ms: int | None = None,
) -> ProgressEntry:
    """Create or update the entry for ``url`` in place.

    Only the fields explicitly passed (``done`` and/or ``note``) are changed; a
    new entry defaults the others. The entry's ``updated_ms`` is bumped so the
    change wins later merges.

    Args:
        progress: The store to mutate.
        url: Guide URL to create or update.
        done: New done state, or ``None`` to leave unchanged.
        note: New note text, or ``None`` to leave unchanged.
        when_ms: Modification timestamp; defaults to now.

    Returns:
        The updated :class:`ProgressEntry`.
    """
    stamp = now_ms() if when_ms is None else when_ms
    entry = progress.get(url)
    if entry is None:
        entry = ProgressEntry(url=url, done=False, note="", updated_ms=stamp)
        progress[url] = entry
    if done is not None:
        entry.done = done
    if note is not None:
        entry.note = note
    entry.updated_ms = stamp
    return entry
