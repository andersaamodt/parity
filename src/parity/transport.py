"""Transport boundary implemented by LAN, Tor, local, or debug adapters elsewhere."""

from __future__ import annotations

from typing import Any, Protocol


class RemoteTransport(Protocol):
    name: str

    def available(self, device: dict[str, Any]) -> bool: ...

    def submit(self, job: dict[str, Any], device: dict[str, Any]) -> dict[str, Any]: ...

