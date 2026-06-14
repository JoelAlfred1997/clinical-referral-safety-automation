#!/usr/bin/env python3
"""Minimal HTTP wrapper around the Phase 6 OpenMRS referral writer.

Uses the Python standard library only (no Flask) so the UiPath performer has a
real REST service to call at WRITEBACK_SERVICE_URL for an AUTO_CREATE decision.
The actual OpenMRS work (find patient, live duplicate guard, idempotent create,
verify-by-reread) is the already-tested Phase 6 code in src/ — this only exposes
it over HTTP so the REFramework performer can orchestrate it alongside the
extraction (:8089) and decision (:8090) services.

Endpoints:
    GET  /health                                  -> {"status": "ok", ...}
    POST /writeback  {"extraction": {...}, "decision": {...}}
        -> finds the matched patient, writes the Referral encounter idempotently
           (keyed on REF-NNN), verifies by re-read, and returns the outcome.

A non-AUTO_CREATE decision is rejected (400) — only clean, safe referrals are
written; HUMAN_REVIEW / BUSINESS_EXCEPTION / SYSTEM_EXCEPTION never reach here.

Run:
    python app.py            # listens on 0.0.0.0:8091 (or $WRITEBACK_SERVICE_PORT)

ALL DATA IS SYNTHETIC. OpenMRS is a mock EPR/EMR.
"""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.metadata import load_metadata  # noqa: E402
from src.openmrs_client import OpenmrsClient  # noqa: E402
from src.referral_writer import (  # noqa: E402
    build_fields, find_active_referrals, find_by_source_id, verify_referral,
    write_referral_idempotent,
)

AUTO_CREATE = "AUTO_CREATE_REFERRAL_RECORD"
__version__ = "1.0.0"


def do_writeback(extraction: dict, decision: dict) -> tuple[int, dict]:
    """Returns (http_status, payload). Mirrors run_referral_writeback.py."""
    ref_id = decision.get("referral_id") or extraction.get("referral_id")
    if decision.get("bot_decision") != AUTO_CREATE:
        return 400, {"error": "writeback is only valid for AUTO_CREATE_REFERRAL_RECORD",
                     "bot_decision": decision.get("bot_decision"), "referral_id": ref_id}

    client = OpenmrsClient()
    if not client.session_authenticated():
        return 503, {"error": "OpenMRS not authenticated / not ready", "referral_id": ref_id}
    metadata = load_metadata()

    nhs = (decision.get("matched_patient") or {}).get("nhs_number")
    patient = client.find_patient_by_nhs(nhs) if nhs else None
    if not patient:
        return 422, {"error": "matched patient not found in OpenMRS",
                     "nhs_number": nhs, "referral_id": ref_id, "action": "NO_PATIENT"}

    # Idempotency first: if THIS referral (same REF-NNN source id) was already
    # written, it is our own prior write — re-verify and return "exists", never a
    # duplicate. Only a *different* referral with the same active speciality is a
    # clinical duplicate (and the decision engine already routes those to review).
    already = find_by_source_id(client, metadata, patient["uuid"], ref_id)
    if already is None:
        spec = (extraction["extraction"].get("specialty") or "").strip().lower()
        dup = [a for a in find_active_referrals(client, metadata, patient["uuid"])
               if (a["speciality"] or "").strip().lower() == spec]
        if dup:
            return 409, {"error": "active referral of the same speciality already exists",
                         "speciality": dup[0]["speciality"], "referral_id": ref_id,
                         "action": "DUPLICATE_BLOCKED"}

    fields = build_fields(extraction, source_id=ref_id, status="active")
    uuid, action = write_referral_idempotent(client, metadata, patient["uuid"], fields)
    ok, mismatches = verify_referral(client, metadata, uuid, fields)
    name_obj = patient["person"]["preferredName"]
    payload = {
        "referral_id": ref_id,
        "synthetic": True,
        "patient_uuid": patient["uuid"],
        "patient_name": f"{name_obj['givenName']} {name_obj['familyName']}",
        "encounter_uuid": uuid,
        "action": action,           # "created" or "exists" (idempotent)
        "verified": bool(ok),
        "mismatches": mismatches or [],
    }
    # A failed verify is a real problem -> 500 so the bot treats it as a system exception.
    return (200 if ok else 500), payload


class Handler(BaseHTTPRequestHandler):
    server_version = "ReferralWriteback/" + __version__

    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        if self.path.rstrip("/") in ("/health", ""):
            self._send(200, {"status": "ok", "service": "writeback", "version": __version__})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        if self.path.rstrip("/") != "/writeback":
            self._send(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) or b"{}"
            body = json.loads(raw.decode("utf-8-sig"))
        except (ValueError, json.JSONDecodeError):
            self._send(400, {"error": "invalid JSON body"})
            return

        extraction = body.get("extraction")
        decision = body.get("decision")
        if not isinstance(extraction, dict) or not isinstance(decision, dict):
            self._send(400, {"error": "provide 'extraction' and 'decision' objects"})
            return

        try:
            code, payload = do_writeback(extraction, decision)
        except Exception as exc:  # OpenMRS / writer failure -> system exception for the bot
            self._send(500, {"error": str(exc), "referral_id": decision.get("referral_id")})
            return

        self._send(code, payload)

    def log_message(self, fmt, *args):  # quieter logging
        sys.stderr.write("[writeback] " + (fmt % args) + "\n")


def main():
    port = int(os.getenv("WRITEBACK_SERVICE_PORT", "8091"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"Writeback service v{__version__} listening on http://0.0.0.0:{port}")
    print("  GET  /health")
    print("  POST /writeback  {\"extraction\": {...}, \"decision\": {...}}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
