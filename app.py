"""Phase 5.c e2e fixture — Python stdlib HTTP server with *deliberately*
deployable-but-awkward defaults.

The fixture's job is to give Deviax's analysis phase material to work
with: hardcoded localhost URLs, a secret-ish constant, SQLite local
state, missing env handling. That way the issue_detection phase emits
rich `<ISSUE>` cards and user_qa asks the canonical
subdomain / database_mode / patch_preference questions.

Routes:
  GET /healthz → 200 "ok"              (used by the post-deploy probe)
  GET /env     → 200 value of GREETING (used by env-var e2e test)
  GET /api/ping → 200 {"service": "...", "upstream": URL}
  GET /api/count → 200 {"hits": N}     (from SQLite, exercises DB path)

No third-party deps — keeps Kaniko build under 30s and keeps the
fixture shippable stand-alone.
"""
from __future__ import annotations

import json
import os
import signal
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- HARDCODED CONFIG (on purpose — triggers IssueCard) -----------------
#
# These are the classic "make it work on my laptop" defaults that a
# fresh project ships with and that should become env vars before
# deploying. Deviax's issue_detection phase should flag them and
# offer env-var injection via the IssueCard "Apply fix" flow.

# Upstream API — in real deployments the customer wires in their own host.
UPSTREAM_API_URL = "http://localhost:4000/api"

# Session secret — hardcoded (BAD). The fixture surfaces this so Deviax's
# secret-detection heuristic can point it out.
SESSION_SECRET = "dev-secret-change-me-before-prod"  # noqa: S105

# Port — hardcoded to 8080. Real deployments want this from PORT env.
LISTEN_PORT = int(os.environ.get("PORT", "8080"))

# Local SQLite file. When Deviax runs issue_detection it should surface
# "you're using SQLite, want a managed Postgres?" via user_qa's
# `database_mode` question.
SQLITE_PATH = "/tmp/counter.db"


def _ensure_db() -> None:
    con = sqlite3.connect(SQLITE_PATH)
    try:
        con.execute(
            "CREATE TABLE IF NOT EXISTS hits ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "ts INTEGER NOT NULL DEFAULT (strftime('%s','now')))"
        )
        con.commit()
    finally:
        con.close()


def _record_hit() -> int:
    con = sqlite3.connect(SQLITE_PATH)
    try:
        con.execute("INSERT INTO hits DEFAULT VALUES")
        row = con.execute("SELECT COUNT(*) FROM hits").fetchone()
        con.commit()
        return int(row[0]) if row else 0
    finally:
        con.close()


class _Handler(BaseHTTPRequestHandler):
    def _respond(self, status: int, body: bytes, ctype: str = "text/plain; charset=utf-8") -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/healthz":
            self._respond(200, b"ok")
            return
        if self.path == "/env":
            value = os.environ.get("GREETING", "").encode("utf-8")
            self._respond(200, value)
            return
        if self.path == "/api/ping":
            body = json.dumps(
                {"service": "e2e-fixture", "upstream": UPSTREAM_API_URL}
            ).encode("utf-8")
            self._respond(200, body, "application/json")
            return
        if self.path == "/api/count":
            n = _record_hit()
            self._respond(200, json.dumps({"hits": n}).encode("utf-8"), "application/json")
            return
        self._respond(404, b"not found")

    def log_message(self, *args: object) -> None:
        return  # quiet in the kaniko build log


if __name__ == "__main__":
    _ensure_db()
    server = HTTPServer(("0.0.0.0", LISTEN_PORT), _Handler)
    
    def _shutdown_handler(signum: int, frame: object) -> None:
        print("Received shutdown signal, closing server...")
        server.shutdown()
    
    signal.signal(signal.SIGTERM, _shutdown_handler)
    signal.signal(signal.SIGINT, _shutdown_handler)
    
    print(f"Server listening on 0.0.0.0:{LISTEN_PORT}")
    server.serve_forever()
    print("Server stopped.")
