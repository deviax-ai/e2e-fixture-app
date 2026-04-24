"""Phase 5.c e2e fixture — minimal Python stdlib HTTP server.

Routes:
  GET /healthz → 200 "ok"
  GET /env     → 200 value of GREETING (empty string if unset)

Emits structured JSON logs on stdout:
  boot, request (per request), heartbeat (every 5s), shutdown (SIGTERM).

No third-party deps — keeps Kaniko build under 30s.
"""
from __future__ import annotations

import json
import os
import signal
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8080
HEARTBEAT_INTERVAL_S = 5.0
_BOOT_TS = time.time()


def _emit(event: str, level: str = "info", **fields: object) -> None:
    payload = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "level": level,
        "event": event,
        **fields,
    }
    sys.stdout.write(json.dumps(payload, separators=(",", ":")) + "\n")
    sys.stdout.flush()


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        started = time.monotonic()
        if self.path == "/healthz":
            status, body = 200, b"ok"
        elif self.path == "/env":
            status, body = 200, os.environ.get("GREETING", "").encode("utf-8")
        else:
            status, body = 404, b""

        self.send_response(status)
        if body:
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

        _emit(
            "request",
            method=self.command,
            path=self.path,
            status=status,
            latency_ms=round((time.monotonic() - started) * 1000, 2),
            client_ip=self.client_address[0],
        )

    def log_message(self, *_args: object) -> None:
        # Suppress BaseHTTPRequestHandler's default stderr line — we emit our own.
        return


def _heartbeat_loop(stop: threading.Event) -> None:
    while not stop.wait(HEARTBEAT_INTERVAL_S):
        _emit("heartbeat", uptime_s=round(time.time() - _BOOT_TS, 1))


def main() -> None:
    httpd = HTTPServer(("0.0.0.0", PORT), _Handler)
    stop = threading.Event()
    hb = threading.Thread(target=_heartbeat_loop, args=(stop,), daemon=True)

    def _shutdown(signum: int, _frame: object) -> None:
        _emit("shutdown", signal=signum, uptime_s=round(time.time() - _BOOT_TS, 1))
        stop.set()
        threading.Thread(target=httpd.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    _emit("boot", port=PORT, greeting_set=bool(os.environ.get("GREETING")))
    hb.start()
    httpd.serve_forever()


if __name__ == "__main__":
    main()
