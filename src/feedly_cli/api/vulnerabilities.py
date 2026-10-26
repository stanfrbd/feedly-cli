"""CVE and vulnerability intelligence endpoints."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from feedly_cli.errors import FeedlyError

from .transport import APITransport


class VulnerabilityAPI:
    def __init__(self, transport: APITransport) -> None:
        self.transport = transport

    def cve(self, cve_id: str) -> Any:
        return self.transport.request(f"/v3/entities/{quote(cve_id, safe='')}")

    def cves(self, cve_ids: list[str], with_stats: bool = False) -> Any:
        if not 1 <= len(cve_ids) <= 100:
            raise FeedlyError("bad_request", "Batch CVE lookup requires between 1 and 100 CVE IDs.")
        params = {"withStats": str(with_stats).lower()} if with_stats else None
        return self.transport.request(
            "/v3/entities/.mget", method="post", params=params, data=cve_ids
        )

    def cve_trending(self, count: int = 10) -> Any:
        if not 1 <= count <= 25:
            raise FeedlyError("bad_request", "Trending CVE count must be between 1 and 25.")
        return self.transport.request("/v3/memes/vulnerabilities/en", params={"count": count})

    def cve_search(
        self,
        payload: dict[str, Any],
        count: int | None = None,
        continuation: str | None = None,
    ) -> Any:
        body = dict(payload)
        if count is not None:
            body["count"] = count
        if continuation is not None:
            body["continuation"] = continuation
        return self.transport.request(
            "/v3/trends/vulnerability-dashboard", method="post", data=body
        )
