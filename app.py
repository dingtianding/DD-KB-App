from __future__ import annotations

import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from rag.generation import GenerationError, answer
from rag.retrieval import SearchIndex


APP_ROOT = Path(__file__).resolve().parent
STATIC = APP_ROOT / "static"
VAULT_ROOT = Path(os.environ.get("DD_KB_VAULT", APP_ROOT.parent / "DD-KB")).resolve()
INDEX = SearchIndex(VAULT_ROOT)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC), **kwargs)

    def _json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "app://obsidian.md")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "app://obsidian.md")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:
        if urlparse(self.path).path == "/api/status":
            refreshed = INDEX.refresh()
            self._json(200, {
                "documents": len({c.path for c in INDEX.chunks}),
                "chunks": len(INDEX.chunks),
                "indexed_at": INDEX.indexed_at,
                "refreshed": refreshed,
            })
            return
        super().do_GET()

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/ask":
            self._json(404, {"error": "Not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 16_384:
                raise ValueError
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError
            question = str(body.get("question", "")).strip()
        except (ValueError, json.JSONDecodeError):
            self._json(400, {"error": "Invalid JSON request."})
            return
        if not question or len(question) > 2_000:
            self._json(400, {"error": "Question must be between 1 and 2,000 characters."})
            return
        sources = INDEX.search(question)
        if not sources:
            self._json(200, {"answer": "I couldn't find relevant material in DD-KB.", "sources": [], "mode": "retrieval"})
            return
        try:
            generated, model = answer(question, sources)
            self._json(200, {"answer": generated, "sources": sources, "mode": "generated", "model": model})
        except GenerationError as error:
            self._json(200, {"answer": str(error), "sources": sources, "mode": "retrieval"})


if __name__ == "__main__":
    print(f"DD-KB is indexing {VAULT_ROOT}")
    print("DD-KB is running at http://127.0.0.1:8787")
    ThreadingHTTPServer(("127.0.0.1", 8787), Handler).serve_forever()
