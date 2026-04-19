"""Phase 5.c e2e fixture — minimal Python stdlib HTTP server.

Routes:
  GET /healthz → 200 "ok"
  GET /env     → 200 value of GREETING (empty string if unset)

No third-party deps — keeps Kaniko build under 30s.
"""
from __future__ import annotations

import os
from http.server import BaseHTTPRequestHandler, HTTPServer


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/healthz":
            body = b"ok"
        elif self.path == "/env":
            body = os.environ.get("GREETING", "").encode("utf-8")
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        return  # quiet in the kaniko build log


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8080), _Handler).serve_forever()
