"""Local HTTP server for the encoder span model (spike, not a benchmark).

Loads the model once and keeps it in memory, so each request costs only the analysis itself.
Binds to 127.0.0.1 by default (local use only).

Start:
  uv run --with torch --with transformers --with sentencepiece --with protobuf \
      python topics/productdev/spike/serve_span.py [--model data/models/span-lt-fixed] [--port 8877]
Use:
  curl -s 127.0.0.1:8877/extract --data-binary @data/interviews/fiktiv-interview-fussgaenger-berlin.txt
  curl -s '127.0.0.1:8877/extract?format=text' --data-binary 'Der Bus fährt nur zweimal am Tag.'
  curl -s 127.0.0.1:8877/extract -H 'Content-Type: application/json' -d '{"text": "..."}'
  curl -s 127.0.0.1:8877/health
The request body is the plain text (UTF-8), or JSON {"text": "..."} with Content-Type
application/json. The answer is JSON (default) or the readable text format (?format=text).
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from span_model import load, predict  # noqa: E402
from try_span import DEFAULT_MODEL, as_json, as_text  # noqa: E402

MAX_BYTES = 2_000_000


class Handler(BaseHTTPRequestHandler):
    model = tokenizer = device = info = None
    lock = threading.Lock()  # one analysis at a time on the GPU

    def _send(self, status: int, body: str, content_type: str) -> None:
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, status: int, payload: dict) -> None:
        self._send(status, json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                   "application/json")

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        if urlparse(self.path).path == "/health":
            self._json(200, {"status": "ok", **self.info})
        else:
            self._json(404, {"error": "use POST /extract or GET /health"})

    def do_POST(self) -> None:  # noqa: N802 - http.server API
        url = urlparse(self.path)
        if url.path != "/extract":
            self._json(404, {"error": "use POST /extract or GET /health"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        if not 0 < length <= MAX_BYTES:
            self._json(400, {"error": f"send a text body of 1 to {MAX_BYTES} bytes"})
            return
        body = self.rfile.read(length).decode("utf-8", errors="replace")
        if "json" in (self.headers.get("Content-Type") or ""):
            try:
                body = json.loads(body)["text"]
            except (ValueError, KeyError, TypeError):
                self._json(400, {"error": 'JSON body must be {"text": "..."}'})
                return
        text = body.strip()
        if not text:
            self._json(400, {"error": "empty text"})
            return
        with self.lock:
            start = time.time()
            relevant, prob, spans = predict(self.model, self.tokenizer, text, self.device)
            seconds = time.time() - start
        if parse_qs(url.query).get("format") == ["text"]:
            self._send(200, as_text(text, relevant, prob, spans, seconds) + "\n", "text/plain")
        else:
            self._json(200, as_json(text, relevant, prob, spans, seconds))

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write(f"{self.log_date_time_string()} {fmt % args}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8877)
    parser.add_argument("--device", default="mps" if torch.backends.mps.is_available() else "cpu")
    args = parser.parse_args()
    start = time.time()
    model, tokenizer = load(args.model, args.device)
    predict(model, tokenizer, "Warm-up.", args.device)
    Handler.model, Handler.tokenizer, Handler.device = model, tokenizer, args.device
    Handler.info = {"model": str(args.model), "device": args.device}
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"model loaded in {time.time() - start:.1f}s; listening on "
          f"http://{args.host}:{args.port} (POST /extract, GET /health)", file=sys.stderr,
          flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
