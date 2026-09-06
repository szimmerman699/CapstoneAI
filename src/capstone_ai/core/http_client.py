import asyncio
import logging
import time
from types import TracebackType

import httpx

from capstone_ai.core.retry import with_retry

logger = logging.getLogger(__name__)


class AsyncHTTPClient:
    def __init__(
        self,
        base_url: str = "",
        timeout: float = 30.0,
        max_concurrent: int = 5,
        max_retries: int = 3,
    ):
        self._base_url = base_url
        self._timeout = timeout
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._max_retries = max_retries
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "AsyncHTTPClient":
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._client:
            await self._client.aclose()

    def _require_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError(
                "AsyncHTTPClient must be used as an async context manager: "
                "`async with AsyncHTTPClient(...) as client:`"
            )
        return self._client

    async def get(self, url: str, **kwargs) -> httpx.Response:
        client = self._require_client()
        async with self._semaphore:
            return await with_retry(
                client.get, url, max_retries=self._max_retries, **kwargs
            )

    async def post(self, url: str, **kwargs) -> httpx.Response:
        client = self._require_client()
        async with self._semaphore:
            return await with_retry(
                client.post, url, max_retries=self._max_retries, **kwargs
            )

    async def get_many(self, urls: list[str]) -> list[httpx.Response]:
        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(self.get(url)) for url in urls]
        return [t.result() for t in tasks]