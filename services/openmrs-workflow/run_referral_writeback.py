#!/usr/bin/env python3
"""Phase 6 write-back: realise AUTO_CREATE decisions as OpenMRS referral records.

For every decision in data/decisions/ whose bot_decision is
AUTO_CREATE_REFERRAL_RECORD, this:
  1. finds the matched patient in OpenMRS (by synthetic NHS number);
  2. runs a live duplicate guard (no active referral of the same speciality);
  3. writes the Referral encounter + obs (idempotent on REF-NNN);
  4. VERIFIES by re-reading the encounter and checking each field round-trips.

HUMAN_REVIEW / BUSINESS_EXCEPTION / SYSTEM_EXCEPTION decisions are NOT written to
OpenMRS — they belong to the review store / exception paths (Phase 9).

Usage:
    python run_referral_writeback.py                 # all AUTO_CREATE decisions
    python run_referral_writeback.py REF-001         # a subset

Needs OpenMRS running, plus setup_referral_metadata.py already run.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.metadata import load_metadata  # noqa: E402
from src.openmrs_client import OpenmrsClient  # noqa: E402
from src.referral_writer import (  # noqa: E402
    build_fields, find_active_referrals, verify_referral, write_referral_idempotent,
)

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_DECISIONS_DIR = os.path.join(_REPO_ROOT, "data", "decisions")
_EXTRACTED_DIR = os.path.join(_REPO_ROOT, "data", "extracted-json")

AUTO_CREATE = "AUTO_CREATE_REFERRAL_RECORD"


def _load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _auto_create_decisions(ids):
    out = []
    if not os.path.isdir(_DECISIONS_DIR):
        return out
    for name in sorted(os.listdir(_DECISIONS_DIR)):
        if not name.endswith(".decision.json"):
            continue
        if ids and not any(name.upper().startswith(i.upper()) for i in ids):
            continue
        decision = _load_json(os.path.join(_DECISIONS_DIR, name))
        if decision.get("bot_decision") == AUTO_CREATE:
            out.append(decision)
    return out


def main() -> int:
    ids = sys.argv[1:]
    client = OpenmrsClient()
    if not client.session_authenticated():
        print(f"OpenMRS not ready / not authenticated at {client.rest}.")
        return 1
    metadata = load_metadata()

    decisions = _auto_create_decisions(ids)
    if not decisions:
        print("No AUTO_CREATE decisions found. Run the Phase 5 engine first "
              "(services/rules-engine/run_decisions.py).")
        return 1

    print(f"{'REF':<8} {'PATIENT':<22} {'ACTION':<9} {'VERIFY':<8} ENCOUNTER")
    print("-" * 92)

    failures = 0
    for decision in decisions:
        ref_id = decision["referral_id"]
        nhs = (decision.get("matched_patient") or {}).get("nhs_number")
        extraction = _load_json(os.path.join(_EXTRACTED_DIR, f"{ref_id}.extracted.json"))

        patient = client.find_patient_by_nhs(nhs) if nhs else None
        if not patient:
            failures += 1
            print(f"{ref_id:<8} {str(nhs):<22} {'NO_PATIENT':<9}")
            continue

        # Live duplicate guard (defensive — AUTO_CREATE should never be a dup).
        spec = (extraction["extraction"].get("specialty") or "").strip().lower()
        dup = [a for a in find_active_referrals(client, metadata, patient["uuid"])
               if (a["speciality"] or "").strip().lower() == spec]
        if dup:
            failures += 1
            print(f"{ref_id:<8} {nhs:<22} {'DUP_BLOCK':<9}  active {dup[0]['speciality']} exists")
            continue

        fields = build_fields(extraction, source_id=ref_id, status="active")
        uuid, action = write_referral_idempotent(client, metadata, patient["uuid"], fields)
        ok, mismatches = verify_referral(client, metadata, uuid, fields)
        if not ok:
            failures += 1
        name = f"{patient['person']['preferredName']['givenName']} {patient['person']['preferredName']['familyName']}"
        print(f"{ref_id:<8} {name:<22} {action:<9} {'OK' if ok else 'FAIL':<8} {uuid}")
        if mismatches:
            for m in mismatches:
                print(f"         verify mismatch: {m}")

    print("-" * 92)
    print(f"Wrote/verified {len(decisions) - failures}/{len(decisions)} AUTO_CREATE referrals"
          + (f"  ({failures} issue(s))" if failures else ""))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
