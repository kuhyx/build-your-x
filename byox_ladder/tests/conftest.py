"""Shared test fixtures.

The autouse network guard mirrors screen-locker/diet_guard: no test may reach
the real GitHub sync transport by accident. Tests that exercise sync patch
``sync_log``/``GitHubSyncClient`` directly, so nothing here ever needs a socket.
"""

from __future__ import annotations

import socket
from typing import TYPE_CHECKING

import pytest

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
