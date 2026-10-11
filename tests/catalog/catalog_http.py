"""A mocked example.org for the catalog's network checks (feature 009 tests)."""

from __future__ import annotations

from collections import Counter

import httpx

ROBOTS_OK = "User-agent: *\nAllow: /\n"


class Web:
    """example.org with configurable answers; counts requests per path."""

    def __init__(self, robots=ROBOTS_OK, status=None, head_status=200, licence_body="CC BY 4.0"):
        self.robots, self.status, self.head_status, self.licence_body = (
            robots,
            status or {},
            head_status,
            licence_body,
        )
        self.calls: Counter = Counter()

    def __call__(self, req: httpx.Request) -> httpx.Response:
        path = req.url.path
        self.calls[(req.method, req.url.host, path)] += 1
        if path == "/robots.txt":
            return httpx.Response(200, text=self.robots)
        if path in ("/.well-known/tdmrep.json", "/ai.txt"):
            return httpx.Response(404)
        if path in self.status:
            return httpx.Response(self.status[path], text="x")
        if path.endswith("/licence"):
            return httpx.Response(200, text=self.licence_body, headers={"content-type": "text/plain"})
        if path.endswith(".zip"):
            if req.method == "HEAD":
                return httpx.Response(self.head_status)
            assert req.headers.get("range") == "bytes=0-0"
            return httpx.Response(206, content=b"P")
        return httpx.Response(
            200,
            text="<html><head></head><body>page</body></html>",
            headers={"content-type": "text/html"},
        )
