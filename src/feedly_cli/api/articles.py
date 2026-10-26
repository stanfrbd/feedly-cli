"""Article lookup and metadata hydration."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from feedly_cli.errors import FeedlyError

from .transport import APITransport


class ArticleAPI:
    def __init__(self, transport: APITransport) -> None:
        self.transport = transport

    def entry(self, entry_id: str) -> Any:
        return self.transport.request(f"/v3/entries/{quote(entry_id, safe='')}")

    def entries(self, entry_ids: list[str]) -> Any:
        if not 1 <= len(entry_ids) <= 100:
            raise FeedlyError(
                "bad_request", "Article metadata lookup requires between 1 and 100 entry IDs."
            )
        return self.transport.request("/v3/entries/.mget", method="post", data=entry_ids)

    def fetch_search_result(self, result: dict[str, Any]) -> dict[str, Any]:
        envelope = dict(result)
        envelope["items"] = self.hydrate_items(list(result.get("items", [])))
        return envelope

    def hydrate_items(self, items: list[Any]) -> list[Any]:
        original_by_id = {
            item["id"]: item for item in items if isinstance(item, dict) and item.get("id")
        }
        ids = list(original_by_id)
        full_by_id: dict[str, dict[str, Any]] = {}
        for start in range(0, len(ids), 100):
            batch = ids[start : start + 100]
            response = self.entries(batch)
            returned = response.get("items", []) if isinstance(response, dict) else response
            if not isinstance(returned, list):
                raise FeedlyError(
                    "api_error",
                    "Feedly returned an invalid response while fetching full article metadata.",
                    details={"expectedCount": len(batch)},
                )
            for item in returned:
                if isinstance(item, dict) and item.get("id"):
                    full_by_id[item["id"]] = item
            missing_ids = [entry_id for entry_id in batch if entry_id not in full_by_id]
            if missing_ids:
                raise FeedlyError(
                    "api_error",
                    "Feedly did not return full metadata for every requested article.",
                    details={"missingCount": len(missing_ids), "missingIds": missing_ids},
                )
        hydrated: list[Any] = []
        for item in items:
            if isinstance(item, dict) and item.get("id"):
                hydrated.append(full_by_id[item["id"]])
            else:
                hydrated.append(item)
        return hydrated
