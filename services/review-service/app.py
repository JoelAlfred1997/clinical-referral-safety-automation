#!/usr/bin/env python3
"""HTTP front door for the human-in-the-loop review store (Phase 9).

Standard-library only (no Flask), matching the extraction (:8089), decision
(:8090) and writeback (:8091) services, so the UiPath ReviewResolver process has
a real REST endpoint to call.

Endpoints:
    GET  /health                       -> {"status": "ok", ...}
    GET  /reviews[?status=PENDING]     -> [ {review row}, ... ]
    POST /reviews/<id>/decision        -> record a clinician decision
         {"reviewer","decision":"APPROVE|REJECT|AMEND","rationale",
          "confirmed_nhs_number"?, "amended_fields"?}
    POST /resolve  {"dry_run"?: bool}  -> bot re-reads decided reviews, applies
                                          outcomes (OpenMRS create / reject),
                                          audits, idempotent -> summary

Run:
    python app.py            # listens on 0.0.0.0:8092 (or $REVIEW_SERVICE_PORT)

ALL DATA IS SYNTHETIC. OpenMRS is a mock EPR/EMR.
"""

from __future__ import annotations

import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import review_store as store  # noqa: E402
import resolve_reviews  # noqa: E402

__version__ = "1.0.0"
_DECISION_RE = re.compile(r"^/reviews/([A-Za-z0-9\-]+)/decision/?$")


class Handler(BaseHTTPRequestHandler):
    server_version = "ReviewService/" + __version__

    def _send(self, code: int, payload) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8-sig") or "{}")

    def do_GET(self):  # noqa: N802
        path = self.path.split("?", 1)[0].rstrip("/")
        if path in ("/health", ""):
            conn = store.connect()
            self._send(200, {"status": "ok", "service": "review", "version": __version__,
                             "counts": store.counts(conn)})
        elif path == "/reviews":
            status = None
            if "?" in self.path:
                from urllib.parse import parse_qs
                status = (parse_qs(self.path.split("?", 1)[1]).get("status") or [None])[0]
            conn = store.connect()
            self._send(200, store.list_reviews(conn, status))
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        path = self.path.rstrip("/")
        try:
            body = self._read_json()
        except ValueError:
            self._send(400, {"error": "invalid JSON body"})
            return

        if path == "/resolve":
            conn = store.connect()
            try:
                summary = resolve_reviews.resolve(conn, dry_run=bool(body.get("dry_run")))
            except Exception as exc:  # noqa: BLE001
                self._send(500, {"error": str(exc)})
                return
            self._send(200, summary)
            return

        m = _DECISION_RE.match(path)
        if m:
            conn = store.connect()
            try:
                row = store.record_decision(
                    conn, m.group(1),
                    reviewer=body.get("reviewer", ""),
                    decision=body.get("decision", ""),
                    rationale=body.get("rationale", ""),
                    confirmed_nhs_number=body.get("confirmed_nhs_number"),
                    amended_fields=body.get("amended_fields"))
            except store.ReviewError as exc:
                self._send(400, {"error": str(exc)})
                return
            self._send(200, row)
            return

        self._send(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        sys.stderr.write("[review] " + (fmt % args) + "\n")


def main():
    port = int(os.getenv("REVIEW_SERVICE_PORT", "8092"))
    store.connect()  # ensure schema exists on boot
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"Review service v{__version__} listening on http://0.0.0.0:{port}")
    print("  GET  /health")
    print("  GET  /reviews[?status=PENDING]")
    print("  POST /reviews/<id>/decision")
    print("  POST /resolve")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
