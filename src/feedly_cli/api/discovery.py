"""Read-only Feedly account discovery resources."""

from __future__ import annotations

from typing import Any

from .transport import APITransport


class DiscoveryAPI:
    def __init__(self, transport: APITransport) -> None:
        self.transport = transport
        self._enterprise_stream_id: str | None = None

    def profile(self) -> Any:
        result = self.transport.request("/v3/profile")
        if isinstance(result, dict):
            enterprise_name = result.get("enterpriseName")
            if isinstance(enterprise_name, str) and enterprise_name:
                self._enterprise_stream_id = f"enterprise/{enterprise_name}/category/global.all"
        return result

    def default_enterprise_stream(self) -> str | None:
        if self._enterprise_stream_id is None:
            profile = self.profile()
            if not isinstance(profile, dict):
                return None
        return self._enterprise_stream_id

    def boards(self) -> Any:
        return self.transport.request("/v3/enterprise/tags")

    def folders(self) -> Any:
        return self.transport.request("/v3/enterprise/collections")

    def feeds(self) -> Any:
        return self.transport.request("/v3/alerts")
