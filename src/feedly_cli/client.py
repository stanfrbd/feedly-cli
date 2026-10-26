"""Thin public facade for the Feedly API resource clients."""

from __future__ import annotations

from types import TracebackType
from typing import Any

from .api.articles import ArticleAPI
from .api.boards import BoardAPI
from .api.discovery import DiscoveryAPI
from .api.search import SearchAPI
from .api.streams import StreamAPI
from .api.transport import DEFAULT_API_BASE, DEFAULT_TIMEOUT, APITransport
from .api.vulnerabilities import VulnerabilityAPI


class FeedlyClient:
    """Compose Feedly resource clients behind a stable public interface."""

    def __init__(
        self,
        token: str | None = None,
        *,
        session: Any = None,
        api_base: str = DEFAULT_API_BASE,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self._transport = APITransport(token, session=session, api_base=api_base, timeout=timeout)
        self.session = self._transport.session
        self.api_base = self._transport.api_base
        self._discovery_api = DiscoveryAPI(self._transport)
        self._stream_api = StreamAPI(self._transport)
        self._article_api = ArticleAPI(self._transport)
        self._board_api = BoardAPI(self._transport, self._stream_api, self._discovery_api)
        self._search_api = SearchAPI(self._transport, self._article_api, self._discovery_api)
        self._vulnerability_api = VulnerabilityAPI(self._transport)

    @property
    def timeout(self) -> int:
        return self._transport.timeout

    @timeout.setter
    def timeout(self, value: int) -> None:
        self._transport.timeout = value
        if hasattr(self.session, "timeout"):
            self.session.timeout = value

    def profile(self) -> Any:
        return self._discovery_api.profile()

    def boards(self) -> Any:
        return self._discovery_api.boards()

    def folders(self) -> Any:
        return self._discovery_api.folders()

    def feeds(self) -> Any:
        return self._discovery_api.feeds()

    def stream_contents(
        self,
        stream_id: str,
        count: int = 20,
        continuation: str | None = None,
        unread_only: bool = False,
    ) -> Any:
        return self._stream_api.contents(stream_id, count, continuation, unread_only)

    def entry(self, entry_id: str) -> Any:
        return self._article_api.entry(entry_id)

    def entries(self, entry_ids: list[str]) -> Any:
        return self._article_api.entries(entry_ids)

    def fetch_search_result(self, result: dict[str, Any]) -> dict[str, Any]:
        return self._article_api.fetch_search_result(result)

    def board_stream(
        self,
        board_id: str,
        count: int = 20,
        continuation: str | None = None,
        unread_only: bool = False,
    ) -> Any:
        return self._board_api.stream(board_id, count, continuation, unread_only)

    def add_entry_to_board(self, board_id: str, entry_id: str) -> Any:
        return self._board_api.add_entry(board_id, entry_id)

    def board_watch(
        self,
        board_id: str,
        count: int = 100,
        max_pages: int = 10,
        continuation: str | None = None,
    ) -> Any:
        return self._board_api.watch(board_id, count, max_pages, continuation)

    def add_url_to_board(
        self,
        board_id: str,
        url: str,
        *,
        dry_run: bool = False,
        stream_id: str | None = None,
        max_pages: int = 10,
        count: int = 100,
    ) -> Any:
        return self._board_api.add_url(
            board_id,
            url,
            dry_run=dry_run,
            stream_id=stream_id,
            max_pages=max_pages,
            count=count,
        )

    def search(
        self,
        query: str | dict[str, Any],
        count: int = 20,
        continuation: str | None = None,
        *,
        stream_id: str | None = None,
    ) -> Any:
        return self._search_api.search(query, count, continuation, stream_id=stream_id)

    def search_all(
        self,
        query: str | dict[str, Any],
        count: int = 100,
        max_pages: int = 100,
        stream_id: str | None = None,
        fetch: bool = False,
    ) -> Any:
        return self._search_api.search_all(query, count, max_pages, stream_id, fetch)

    def cve(self, cve_id: str) -> Any:
        return self._vulnerability_api.cve(cve_id)

    def cves(self, cve_ids: list[str], with_stats: bool = False) -> Any:
        return self._vulnerability_api.cves(cve_ids, with_stats)

    def cve_trending(self, count: int = 10) -> Any:
        return self._vulnerability_api.cve_trending(count)

    def cve_search(
        self,
        payload: dict[str, Any],
        count: int | None = None,
        continuation: str | None = None,
    ) -> Any:
        return self._vulnerability_api.cve_search(payload, count, continuation)

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> FeedlyClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
