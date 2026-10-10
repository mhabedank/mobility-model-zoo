"""A local static server for the built site, under the same path prefix as GitHub Pages, so a
wrong relative link shows up in the preview (contracts/cli.md, `zoo site serve`)."""

from __future__ import annotations

import functools
import http.server
import threading
from pathlib import Path

PREFIX = "/mobility-model-zoo"


class _Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        if path.split("?", 1)[0].startswith(PREFIX):
            path = path[len(PREFIX) :] or "/"
        else:
            path = "/__outside_prefix__"
        return super().translate_path(path)

    def send_error(self, code: int, message: str | None = None, explain: str | None = None) -> None:
        page = Path(self.directory) / "404.html"
        if code == 404 and page.exists():
            body = page.read_bytes()
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().send_error(code, message, explain)

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - signature of the base class
        pass


def server(out: Path, port: int = 0) -> http.server.ThreadingHTTPServer:
    handler = functools.partial(_Handler, directory=str(out.resolve()))
    return http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)


def serve(out: Path, port: int) -> None:
    server(out, port).serve_forever()


def background(out: Path) -> tuple[http.server.ThreadingHTTPServer, str]:
    """A server on a free port in a daemon thread, and the base URL of the site."""
    srv = server(out, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}{PREFIX}/"
