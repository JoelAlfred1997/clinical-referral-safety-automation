#!/usr/bin/env python3
"""Minimal HTTP wrapper around the extraction pipeline.

Uses the Python standard library only (no Flask dependency) so the UiPath
performer has a real REST service to call at EXTRACTION_SERVICE_URL.

Endpoints:
    GET  /health                      -> {"status": "ok", ...}
    POST /extract  {"path": "..."}     -> extract a local file
    POST /extract  {"source_file":"x", "text":"..."} -> extract supplied text

Run:
    python app.py            # listens on 0.0.0.0:8089 (or $EXTRACTION_SERVICE_PORT)
"""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import __version__  # noqa: E402
from src.extractor import extract_referral, extract_referral_text  # noqa: E402


class Handler(BaseHTTPRequestHandler):
    server_version = "ReferralExtraction/" + __version__

    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        if self.path.rstrip("/") in ("/health", ""):
            self._send(200, {"status": "ok", "service": "extraction", "version": __version__})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        if self.path.rstrip("/") != "/extract":
            self._send(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._send(400, {"error": "invalid JSON body"})
            return

        try:
            if body.get("path"):
                result = extract_referral(body["path"])
            elif body.get("text") is not None:
                result = extract_referral_text(body.get("source_file", "REF-000.txt"), body["text"])
            else:
                self._send(400, {"error": "provide 'path' or 'source_file'+'text'"})
                return
        except Exception as exc:  # extraction/schema failure
            self._send(500, {"error": str(exc)})
            return

        self._send(200, result)

    def log_message(self, fmt, *args):  # quieter logging
        sys.stderr.write("[extraction] " + (fmt % args) + "\n")


def main():
    port = int(os.getenv("EXTRACTION_SERVICE_PORT", "8089"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"Extraction service v{__version__} listening on http://0.0.0.0:{port}")
    print("  GET  /health")
    print("  POST /extract  {\"path\": \"...\"}  |  {\"source_file\":\"x\",\"text\":\"...\"}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
