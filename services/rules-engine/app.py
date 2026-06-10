#!/usr/bin/env python3
"""Minimal HTTP wrapper around the decision engine.

Uses the Python standard library only (no Flask dependency) so the UiPath
performer has a real REST service to call at DECISION_SERVICE_URL after it has
the extraction JSON.

Endpoints:
    GET  /health                          -> {"status": "ok", ...}
    POST /decide  {"extraction": {...}}     -> decide from an extraction result
    POST /decide  {"extraction": {...}, "source": "openmrs"}  -> match live

The body's "extraction" is a Phase 4 extraction result (the object the
extraction service returns). "source" selects the patient-match backend:
"local" (seed file, default) or "openmrs" (live REST).

Run:
    python app.py            # listens on 0.0.0.0:8090 (or $DECISION_SERVICE_PORT)
"""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import __version__  # noqa: E402
from src.decision_engine import decide_for_extraction  # noqa: E402
from src.patient_repository import get_patient_repository  # noqa: E402


class Handler(BaseHTTPRequestHandler):
    server_version = "ReferralDecision/" + __version__

    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        if self.path.rstrip("/") in ("/health", ""):
            self._send(200, {"status": "ok", "service": "decision", "version": __version__})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        if self.path.rstrip("/") != "/decide":
            self._send(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) or b"{}"
            # Tolerate a UTF-8 BOM some clients (e.g. Windows PowerShell) prepend.
            body = json.loads(raw.decode("utf-8-sig"))
        except (ValueError, json.JSONDecodeError):
            self._send(400, {"error": "invalid JSON body"})
            return

        extraction = body.get("extraction")
        if not isinstance(extraction, dict):
            self._send(400, {"error": "provide an 'extraction' object (a Phase 4 result)"})
            return

        try:
            repo = get_patient_repository(body.get("source", "local"))
            result = decide_for_extraction(extraction, repo)
        except Exception as exc:  # matching/rules/schema failure
            self._send(500, {"error": str(exc)})
            return

        self._send(200, result)

    def log_message(self, fmt, *args):  # quieter logging
        sys.stderr.write("[decision] " + (fmt % args) + "\n")


def main():
    port = int(os.getenv("DECISION_SERVICE_PORT", "8090"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"Decision service v{__version__} listening on http://0.0.0.0:{port}")
    print("  GET  /health")
    print("  POST /decide  {\"extraction\": {...}, \"source\": \"local|openmrs\"}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
