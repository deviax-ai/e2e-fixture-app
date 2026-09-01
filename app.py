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
  GET /api/notes?msg=hi → 200 {"added": "hi", "notes": [...]}
                                       (write+read DB, visible from browser)

No third-party deps — keeps Kaniko build under 30s and keeps the
fixture shippable stand-alone.
"""
from __future__ import annotations

import json
import logging
import os
import signal
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlsplit

# --- logging ------------------------------------------------------------
#
# stdlib logging to stdout so `kubectl logs` / docker logs surface every
# request. Format is intentionally simple but timestamped.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("e2e-fixture")
log.info("e2e-fixture starting up (rev 9)")

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
LISTEN_PORT = 8080

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
        con.execute(
            "CREATE TABLE IF NOT EXISTS notes ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "msg TEXT NOT NULL, "
            "ts INTEGER NOT NULL DEFAULT (strftime('%s','now')))"
        )
        con.commit()
        log.info("db ready path=%s", SQLITE_PATH)
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


def _add_note(msg: str) -> list[dict[str, object]]:
    con = sqlite3.connect(SQLITE_PATH)
    try:
        con.execute("INSERT INTO notes (msg) VALUES (?)", (msg,))
        con.commit()
        rows = con.execute(
            "SELECT id, msg, ts FROM notes ORDER BY id DESC LIMIT 20"
        ).fetchall()
        return [{"id": r[0], "msg": r[1], "ts": r[2]} for r in rows]
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
        parts = urlsplit(self.path)
        path = parts.path
        log.info("request method=GET path=%s remote=%s", self.path, self.client_address[0])

        if path == "/" or path == "/healthz":
            self._respond(200, b"ok")
            return
        if path == "/env":
            value = os.environ.get("GREETING", "").encode("utf-8")
            self._respond(200, value)
            return
        if path == "/api/ping":
            body = json.dumps(
                {"service": "e2e-fixture", "upstream": UPSTREAM_API_URL}
            ).encode("utf-8")
            self._respond(200, body, "application/json")
            return
        if path == "/api/count":
            n = _record_hit()
            log.info("hit recorded total=%d", n)
            self._respond(200, json.dumps({"hits": n}).encode("utf-8"), "application/json")
            return
        if path == "/api/notes":
            qs = parse_qs(parts.query)
            msg = (qs.get("msg", [""])[0] or "").strip()
            if not msg:
                self._respond(
                    400,
                    json.dumps({"error": "missing ?msg=... query param"}).encode("utf-8"),
                    "application/json",
                )
                return
            notes = _add_note(msg)
            log.info("note added msg=%r total=%d", msg, len(notes))
            self._respond(
                200,
                json.dumps({"added": msg, "notes": notes}).encode("utf-8"),
                "application/json",
            )
            return
        log.warning("not found path=%s", self.path)
        self._respond(404, b"not found")

    def log_message(self, *args: object) -> None:
        # default access log is noisy & unstructured; we log via `log` instead.
        return


def _shutdown_handler(signum: int, frame: object) -> None:
    log.info("received signal=%d, shutting down gracefully", signum)
    sys.exit(0)


if __name__ == "__main__":
    _ensure_db()
    signal.signal(signal.SIGTERM, _shutdown_handler)
    signal.signal(signal.SIGINT, _shutdown_handler)
    log.info("listening port=%d", LISTEN_PORT)
    try:
        HTTPServer(("0.0.0.0", LISTEN_PORT), _Handler).serve_forever()
    except KeyboardInterrupt:
        log.info("interrupted, exiting")
    except SystemExit:
        log.info("clean exit")
