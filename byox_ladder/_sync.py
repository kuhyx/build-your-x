"""Cross-device sync for the progress store, via the shared crdt_sync layer.

Progress is mirrored through a private GitHub repo using the same
Hybrid-Logical-Clock CRDT scheme diet_guard and screen-locker use: each device
writes ``<path_prefix>/<device_id>/log.json`` and merges every other device's
file on each sync tick (last-writer-wins per field, ordered by HLC).

Sync is **optional**: with no token configured the CLI works fully offline and
``run_sync`` reports ``unconfigured`` rather than erroring (mirroring
screen-locker's fallback contract). A network/auth failure is logged and
surfaced, never raised past this boundary — a failed sync must not crash
``byox``.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import os
from pathlib import Path
import socket
from typing import Any, Literal

from crdt_sync import GitHubSyncClient, GitHubSyncError, Hlc, Record, sync_log

from byox_ladder._progress import (
    PROGRESS_PATH,
    Progress,
    ProgressEntry,
    load_progress,
    save_progress,
)

logger = logging.getLogger(__name__)

# Non-secret sync configuration. One shared repo, one per-app path prefix —
# the same convention diet_guard uses (repo "syncs", prefix per app).
SYNC_REPO_OWNER = "kuhyx"
SYNC_REPO_NAME = "syncs"
SYNC_PATH_PREFIX = "byox-ladder/devices"
SYNC_TIMEOUT_SECONDS = 10.0

# Fine-grained GitHub PAT (contents read/write on the sync repo), mode 600.
SYNC_TOKEN_FILE = Path.home() / ".config" / "byox_ladder" / "sync_token"


@dataclass
class SyncOutcome:
    """Result of a sync attempt.

    Attributes:
        status: ``"ok"`` on success, ``"unconfigured"`` when no token is set
            (a benign offline no-op), ``"error"`` on a network/auth failure.
        total: Number of tracked guides after the merge.
        done: Number of those marked done.
        detail: Error message when ``status == "error"``, else the token path
            for ``"unconfigured"`` (empty otherwise).
    """

    status: Literal["ok", "unconfigured", "error"]
    total: int
    done: int
    detail: str


def device_id() -> str:
    """Return this device's sync id (``$BYOX_DEVICE_ID`` or the hostname)."""
    return os.environ.get("BYOX_DEVICE_ID") or socket.gethostname()


def read_token(path: Path = SYNC_TOKEN_FILE) -> str | None:
    """Read the sync token, or ``None`` if it is missing or empty.

    Args:
        path: Token file location.

    Returns:
        The stripped token string, or ``None`` when unconfigured.
    """
    try:
        token = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return token or None


def progress_to_log(progress: Progress, node_id: str) -> dict[str, Any]:
    """Convert the local store to a crdt_sync log keyed by guide URL.

    Both fields of an entry share one HLC seeded from its ``updated_ms``; the
    domain is small enough that whole-entry last-writer-wins is the intended
    merge behaviour.

    Args:
        progress: The local progress store.
        node_id: This device's id (the HLC node component).

    Returns:
        A ``{url: Record}`` log ready for :func:`crdt_sync.sync_log`.
    """
    log: dict[str, Any] = {}
    for url, entry in progress.items():
        hlc = Hlc.new_tick(node_id, wall_time_ms=entry.updated_ms)
        log[url] = Record(
            id=url,
            fields={"done": (entry.done, hlc), "note": (entry.note, hlc)},
        )
    return log


def log_to_progress(log: dict[str, Any]) -> Progress:
    """Convert a merged crdt_sync log back into the local store.

    Tombstoned records are skipped. Each entry's ``updated_ms`` is taken from
    the latest field HLC so a subsequent local edit still orders correctly.

    Args:
        log: A merged ``{url: Record}`` log from :func:`crdt_sync.sync_log`.

    Returns:
        The reconstructed progress store.
    """
    progress: Progress = {}
    for url, record in log.items():
        if record.deleted:
            continue
        done_field = record.fields.get("done")
        note_field = record.fields.get("note")
        done = bool(done_field[0]) if done_field else False
        note = str(note_field[0]) if note_field else ""
        updated_ms = 0
        for field in (done_field, note_field):
            if field is not None:
                updated_ms = max(updated_ms, field[1].wall_time_ms)
        progress[url] = ProgressEntry(
            url=url, done=done, note=note, updated_ms=updated_ms
        )
    return progress


def _encode(log: dict[str, Any]) -> str:
    """Serialize a log to the canonical crdt_sync JSON format."""
    return json.dumps({key: record.to_dict() for key, record in log.items()})


def _decode(text: str) -> dict[str, Any]:
    """Parse the canonical crdt_sync JSON back into a ``{url: Record}`` log."""
    return {key: Record.from_dict(value) for key, value in json.loads(text).items()}


def run_sync(
    progress_path: Path = PROGRESS_PATH,
    token_file: Path = SYNC_TOKEN_FILE,
) -> SyncOutcome:
    """Pull, merge, and push the progress store across devices.

    Reads the local store, merges it with every other device's log via
    :func:`crdt_sync.sync_log`, writes the merged result back locally, and
    pushes this device's copy.

    Args:
        progress_path: Local progress store location.
        token_file: Sync token file location.

    Returns:
        A :class:`SyncOutcome` describing what happened (never raises for an
        unconfigured token or a sync failure).
    """
    token = read_token(token_file)
    if token is None:
        return SyncOutcome("unconfigured", 0, 0, str(token_file))

    node = device_id()
    local = load_progress(progress_path)
    local_log = progress_to_log(local, node)
    client = GitHubSyncClient(
        SYNC_REPO_OWNER, SYNC_REPO_NAME, token, timeout_seconds=SYNC_TIMEOUT_SECONDS
    )
    try:
        merged = sync_log(
            client=client,
            device_id=node,
            path_prefix=SYNC_PATH_PREFIX,
            local_log=local_log,
            encode=_encode,
            decode=_decode,
        )
    except GitHubSyncError as exc:
        logger.warning("sync failed: %s", exc)
        return SyncOutcome("error", 0, 0, str(exc))

    merged_progress = log_to_progress(merged)
    save_progress(progress_path, merged_progress)
    total = len(merged_progress)
    done = sum(1 for entry in merged_progress.values() if entry.done)
    return SyncOutcome("ok", total, done, "")
