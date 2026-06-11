#!/usr/bin/env python3
"""Phase 6 acceptance harness — proves the concrete OpenMRS update path.

Runs end-to-end against a live OpenMRS and asserts:

  * the Referral encounter type + all referral concepts exist (metadata setup);
  * the pre-existing active Cardiology referral for Arthur Reed is present, so the
    LIVE duplicate check has something to detect;
  * each AUTO_CREATE decision (REF-001/002/003) is written as a Referral encounter
    and VERIFIED by re-read (every field round-trips);
  * the write is IDEMPOTENT (a second run creates no duplicate encounter);
  * a same-speciality referral for Reed is detected as a DUPLICATE by querying
    OpenMRS (the live equivalent of the Phase 5 decision);
  * the live existing_referral_status matches the seed value Phase 5 used.

It is self-contained: it (re)generates extraction + decisions, ensures metadata,
and seeds the fixture, then checks. Re-running is safe (idempotent writes).

Exit code 0 = all gate checks pass.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.metadata import REFERRAL_CONCEPTS, ensure_referral_metadata  # noqa: E402
from src.openmrs_client import OpenmrsClient  # noqa: E402
from src.referral_writer import (  # noqa: E402
    build_fields, existing_referral_status, find_active_referrals,
    find_by_source_id, get_referral_encounters, verify_referral,
    write_referral_idempotent,
)

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_EXTRACTED_DIR = os.path.join(_REPO_ROOT, "data", "extracted-json")
_DECISIONS_DIR = os.path.join(_REPO_ROOT, "data", "decisions")
_EXTRACTION_DIR = os.path.join(_REPO_ROOT, "services", "extraction-service")
_RULES_DIR = os.path.join(_REPO_ROOT, "services", "rules-engine")

REED_NHS = "9990000336"
GREEN, RED, YELLOW, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"
_results = []


def _line(label, ok, detail=""):
    tag = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
    suffix = f"  {DIM}{detail}{RESET}" if (detail and not ok) else ""
    _results.append(ok)
    return f"  [{tag}] {label}{suffix}"


def _run(cmd, cwd):
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stdout[-2000:])
        print(proc.stderr[-1000:])
    return proc.returncode == 0


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    client = OpenmrsClient()
    print("Phase 6 acceptance - OpenMRS referral workflow\n")

    # C1 -----------------------------------------------------------------
    auth = client.session_authenticated()
    print(_line("OpenMRS REST authenticated", auth, f"at {client.rest}"))
    if not auth:
        print("\nStart it: docker compose -f openmrs-setup/docker-compose.yml up -d")
        return 1

    print(f"{DIM}Regenerating extraction + decisions (Phase 4 + 5)...{RESET}")
    if not _run([sys.executable, "run_extraction.py"], _EXTRACTION_DIR):
        return 1
    if not _run([sys.executable, "run_decisions.py"], _RULES_DIR):
        return 1

    # C2 metadata --------------------------------------------------------
    metadata = ensure_referral_metadata(client, save=True)
    et_ok = bool(metadata.get("encounter_type_uuid"))
    concepts_ok = all(k in metadata["concepts"] for k in REFERRAL_CONCEPTS)
    print(_line("Referral encounter type exists", et_ok, metadata.get("encounter_type_uuid")))
    print(_line(f"All {len(REFERRAL_CONCEPTS)} referral concepts exist", concepts_ok,
                str(list(metadata["concepts"]))))

    # C3 seed Reed's pre-existing active Cardiology referral --------------
    if not _run([sys.executable, "seed_existing_referrals.py"], os.path.dirname(__file__)):
        return 1
    reed = client.find_patient_by_nhs(REED_NHS)
    reed_status = existing_referral_status(client, metadata, reed["uuid"]) if reed else "none"
    print(_line("Reed has pre-existing active:Cardiology", reed_status == "active:Cardiology",
                reed_status))

    # C4 write + verify the AUTO_CREATE referrals ------------------------
    auto = [d for d in
            (_load(os.path.join(_DECISIONS_DIR, n)) for n in sorted(os.listdir(_DECISIONS_DIR))
             if n.endswith(".decision.json"))
            if d.get("bot_decision") == "AUTO_CREATE_REFERRAL_RECORD"]
    print(_line("3 AUTO_CREATE decisions to write", len(auto) == 3, f"got {len(auto)}"))

    first_ref = None
    for d in auto:
        ref_id = d["referral_id"]
        nhs = (d.get("matched_patient") or {}).get("nhs_number")
        extraction = _load(os.path.join(_EXTRACTED_DIR, f"{ref_id}.extracted.json"))
        patient = client.find_patient_by_nhs(nhs)
        fields = build_fields(extraction, source_id=ref_id, status="active")
        uuid, _action = write_referral_idempotent(client, metadata, patient["uuid"], fields)
        ok, mism = verify_referral(client, metadata, uuid, fields)
        print(_line(f"{ref_id} written + verified by re-read", ok, "; ".join(mism)))
        if first_ref is None:
            first_ref = (ref_id, patient["uuid"], fields)

    # C5 idempotency -----------------------------------------------------
    ref_id, patient_uuid, fields = first_ref
    _uuid2, action2 = write_referral_idempotent(client, metadata, patient_uuid, fields)
    count = len([e for e in get_referral_encounters(client, metadata, patient_uuid)
                 if e["fields"].get("source_id") == ref_id])
    print(_line(f"Idempotent: re-writing {ref_id} creates no duplicate",
                action2 == "exists" and count == 1, f"action={action2} count={count}"))

    # C6 live duplicate detection (REF-007 = Cardiology for Reed) --------
    active = find_active_referrals(client, metadata, reed["uuid"])
    cardiology_active = any((a["speciality"] or "").lower() == "cardiology" for a in active)
    print(_line("Live duplicate check sees Reed's active Cardiology referral",
                cardiology_active, str(active)))

    # C7 live == seed parity (what Phase 5 decided on) -------------------
    seed = _load(os.path.join(_REPO_ROOT, "data", "synthetic-patients", "synthetic_patients.json"))
    reed_seed = next((p for p in seed if p["nhs_number"] == REED_NHS), {})
    parity = reed_status == reed_seed.get("existing_referral_status")
    print(_line("Live existing_referral_status matches the seed Phase 5 used", parity,
                f"live={reed_status} seed={reed_seed.get('existing_referral_status')}"))

    passed = sum(1 for r in _results if r)
    total = len(_results)
    print("\n" + "=" * 60)
    print(f"GATE RESULT: {passed}/{total} Phase 6 checks pass")
    print("=" * 60)
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
