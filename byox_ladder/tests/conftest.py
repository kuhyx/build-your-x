"""Shared test fixtures.

The autouse network guard mirrors screen-locker/diet_guard: no test may reach
the real GitHub sync transport by accident. Tests that exercise sync patch
``sync_log``/``GitHubSyncClient`` directly, so nothing here ever needs a socket.
"""

from __future__ import annotations

import pathlib
import socket
from typing import TYPE_CHECKING

import pytest

from byox_ladder import _sync

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(autouse=True)
def _block_real_network(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Fail loudly if any test opens a real network connection."""

    def _guard(*_args: object, **_kwargs: object) -> None:
        message = "real network access is blocked in tests"
        raise RuntimeError(message)

    monkeypatch.setattr(socket.socket, "connect", _guard)
    return


@pytest.fixture(autouse=True)
def _no_real_firebase_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
) -> None:
    """Point the Firebase config at a path that does not exist.

    ``_remote_client`` reads ``crdt_sync.CONFIG_FILE`` to decide whether to
    build a Firebase-primary mirror. On a developer machine that file *does*
    exist, so without this every sync test would try to sign in over the
    network -- which the guard above then fails, in the fixture rather than in
    the code under test. Tests that want the Firebase path point it back at a
    file they control.
    """
    monkeypatch.setattr(
        _sync, "CONFIG_FILE", pathlib.Path("/nonexistent/firebase.json")
    )
