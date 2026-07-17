"""``byox`` command-line interface for the progress tracker.

Subcommands:

* ``done <guide> [--note TEXT]`` — mark a guide complete (and optionally record
  where you built it).
* ``undone <guide>`` — clear a guide's done state.
* ``note <guide> <text>`` — set/replace a guide's note.
* ``status`` — overall and per-tier progress plus the list of done guides.
* ``build`` — regenerate the HTML ladder pages (delegates to build_pages).

A guide is named loosely (URL, url-slug fragment, or title words); see
:mod:`byox_ladder._resolve`.
"""

from __future__ import annotations

import argparse
import logging
import sys

from byox_ladder import build_pages
from byox_ladder._progress import PROGRESS_PATH, load_progress, mark, save_progress
from byox_ladder._resolve import Guide, GuideResolutionError, load_guides, resolve
from byox_ladder._sync import run_sync

# Difficulty tiers in ascending order, for the status breakdown.
TIER_ORDER = ["beginner", "intermediate", "advanced", "expert", "unsorted"]


def _emit(message: str) -> None:
    """Write a line to stdout (kept separate so tests can capture output)."""
    sys.stdout.write(message + "\n")


def _done_count(guides: list[Guide], done_urls: set[str]) -> int:
    """Return how many of ``guides`` are marked done."""
    return sum(1 for guide in guides if guide["url"] in done_urls)


def _cmd_done(args: argparse.Namespace) -> int:
    """Handle ``byox done`` — mark a guide complete, with an optional note."""
    guides = load_guides()
    guide = resolve(args.guide, guides)
    progress = load_progress(PROGRESS_PATH)
    mark(progress, guide["url"], done=True, note=args.note)
    save_progress(PROGRESS_PATH, progress)
    done_urls = {url for url, entry in progress.items() if entry.done}
    _emit(f"✓ {guide['title']}  ({_done_count(guides, done_urls)}/{len(guides)})")
    return 0


def _cmd_undone(args: argparse.Namespace) -> int:
    """Handle ``byox undone`` — clear a guide's done state."""
    guides = load_guides()
    guide = resolve(args.guide, guides)
    progress = load_progress(PROGRESS_PATH)
    mark(progress, guide["url"], done=False)
    save_progress(PROGRESS_PATH, progress)
    done_urls = {url for url, entry in progress.items() if entry.done}
    _emit(f"○ {guide['title']}  ({_done_count(guides, done_urls)}/{len(guides)})")
    return 0


def _cmd_note(args: argparse.Namespace) -> int:
    """Handle ``byox note`` — set or replace a guide's note."""
    guides = load_guides()
    guide = resolve(args.guide, guides)
    progress = load_progress(PROGRESS_PATH)
    mark(progress, guide["url"], note=args.text)
    save_progress(PROGRESS_PATH, progress)
    _emit(f"noted {guide['title']}: {args.text}")
    return 0


def _cmd_status(_args: argparse.Namespace) -> int:
    """Handle ``byox status`` — overall + per-tier progress and the done list."""
    guides = load_guides()
    progress = load_progress(PROGRESS_PATH)
    done_urls = {url for url, entry in progress.items() if entry.done}

    total = len(guides)
    done = _done_count(guides, done_urls)
    _emit(f"Progress: {done}/{total} guides done")

    # Per-tier [done, total] tallies.
    tiers: dict[str, list[int]] = {}
    for guide in guides:
        tally = tiers.setdefault(guide["tier"], [0, 0])
        tally[0] += 1 if guide["url"] in done_urls else 0
        tally[1] += 1
    for tier in TIER_ORDER:
        if tier in tiers:
            tally = tiers[tier]
            _emit(f"  {tier:<12} {tally[0]}/{tally[1]}")

    done_guides = [guide for guide in guides if guide["url"] in done_urls]
    if done_guides:
        _emit("Done:")
        for guide in done_guides:
            entry = progress[guide["url"]]
            suffix = f"  — {entry.note}" if entry.note else ""
            _emit(f"  ✓ {guide['title']}{suffix}")
    return 0


def _cmd_build(_args: argparse.Namespace) -> int:
    """Handle ``byox build`` — regenerate the HTML ladder pages."""
    return build_pages.main()


def _cmd_sync(_args: argparse.Namespace) -> int:
    """Handle ``byox sync`` — merge progress across devices via crdt_sync."""
    outcome = run_sync()
    if outcome.status == "unconfigured":
        _emit(f"sync skipped: no token at {outcome.detail} (byox works offline)")
        return 0
    if outcome.status == "error":
        _emit(f"sync failed: {outcome.detail}")
        return 1
    _emit(f"synced: {outcome.done}/{outcome.total} tracked guides done across devices")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    """Construct the argparse parser with all subcommands."""
    parser = argparse.ArgumentParser(prog="byox", description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)

    done = subs.add_parser("done", help="mark a guide complete")
    done.add_argument("guide", help="URL, slug fragment, or title words")
    done.add_argument("--note", default=None, help="where/how you built it")

    undone = subs.add_parser("undone", help="clear a guide's done state")
    undone.add_argument("guide", help="URL, slug fragment, or title words")

    note = subs.add_parser("note", help="set a guide's note")
    note.add_argument("guide", help="URL, slug fragment, or title words")
    note.add_argument("text", help="note text")

    subs.add_parser("status", help="show progress")
    subs.add_parser("build", help="regenerate the HTML ladder pages")
    subs.add_parser("sync", help="sync progress across devices")
    return parser


# Dispatch table: subcommand name -> handler.
_HANDLERS = {
    "done": _cmd_done,
    "undone": _cmd_undone,
    "note": _cmd_note,
    "status": _cmd_status,
    "build": _cmd_build,
    "sync": _cmd_sync,
}


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and run the selected subcommand.

    Args:
        argv: Argument vector (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code (0 on success, 1 on a resolution/data error).
    """
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _build_parser().parse_args(argv)
    try:
        return _HANDLERS[args.command](args)
    except GuideResolutionError as exc:
        _emit(f"error: {exc}")
        for candidate in exc.candidates:
            _emit(f"  - {candidate['title']}  {candidate['url']}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
