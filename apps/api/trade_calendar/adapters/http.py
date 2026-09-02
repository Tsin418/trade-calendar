from collections.abc import Mapping

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from trade_calendar.adapters.errors import (
    HttpStatusError,
    NetworkError,
    PayloadTooLargeError,
    RateLimitError,
)
from trade_calendar.adapters.types import RawPayload


class HttpFetcher:
    def __init__(
        self,
        *,
        user_agent: str,
        timeout_seconds: float = 20,
        max_bytes: int = 10 * 1024 * 1024,
    ) -> None:
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds
        self.max_bytes = max_bytes

    @retry(
        retry=retry_if_exception_type((NetworkError, HttpStatusError)),
        wait=wait_exponential(multiplier=1, min=1, max=15),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def get(
        self, source_key: str, url: str, headers: Mapping[str, str] | None = None
    ) -> RawPayload:
        request_headers = {"User-Agent": self.user_agent, "Accept": "*/*"}
        request_headers.update(headers or {})
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout_seconds), follow_redirects=True
            ) as client:
                response = await client.get(url, headers=request_headers)
        except httpx.HTTPError as exc:
            raise NetworkError(str(exc)) from exc
        if response.status_code == 429:
            raise RateLimitError("source rate limited the request")
        if response.status_code >= 500:
            raise HttpStatusError(f"upstream returned {response.status_code}")
        if response.status_code >= 400:
            error = HttpStatusError(f"upstream returned {response.status_code}")
            error.retryable = False
            raise error
        if len(response.content) > self.max_bytes:
            raise PayloadTooLargeError(
                f"payload is {len(response.content)} bytes, limit is {self.max_bytes}"
            )
        return RawPayload(
            source_key=source_key,
            url=str(response.url),
            content=response.content,
            content_type=response.headers.get("content-type", "application/octet-stream"),
            http_status=response.status_code,
            headers={
                key: value
                for key, value in response.headers.items()
                if key.lower() in {"etag", "last-modified", "content-type"}
            },
        )

