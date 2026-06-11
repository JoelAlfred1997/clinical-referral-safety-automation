#!/usr/bin/env python3
"""Phase 6 seed: pre-existing active referrals (the duplicate-check fixtures).

Reads the synthetic-patient seed file and, for every patient whose
``existing_referral_status`` is ``active:<Speciality>`` (currently Arthur Reed,
9990000336, active:Cardiology), writes that pre-existing active Referral
encounter into OpenMRS. This is what makes the LIVE duplicate-referral check
detectable — REF-007 (a new Cardiology referral for Reed) then collides with it.

Idempotent: keyed on a stable source id, so re-running does not duplicate.

Usage:
    python seed_existing_referrals.py

Needs OpenMRS running and setup_referral_metadata.py already run.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.metadata import load_metadata  # noqa: E402
from src.openmrs_client import OpenmrsClient  # noqa: E402
from src.referral_writer import _now_offset, write_referral_idempotent  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SEED_FILE = _REPO_ROOT / "data" / "synthetic-patients" / "synthetic_patients.json"


def _parse_active_specialty(status: str) -> str | None:
    if not status or ":" not in status:
        return None
    state, _, spec = status.partition(":")
    return spec.strip() if state.strip().lower() == "active" and spec.strip() else None


def main() -> int:
    client = OpenmrsClient()
    if not client.session_authenticated():
        print(f"OpenMRS not ready / not authenticated at {client.rest}.")
        return 1
    metadata = load_metadata()

    patients = json.loads(_SEED_FILE.read_text(encoding="utf-8"))
    targets = [p for p in patients if _parse_active_specialty(p.get("existing_referral_status", ""))]
    if not targets:
        print("No patients with an active pre-existing referral to seed.")
        return 0

    created = exists = failed = 0
    for p in targets:
        spec = _parse_active_specialty(p["existing_referral_status"])
        nhs = p["nhs_number"]
        patient = client.find_patient_by_nhs(nhs)
        if not patient:
            failed += 1
            print(f"  FAIL: patient {nhs} ({p['first_name']} {p['last_name']}) not found in OpenMRS")
            continue
        fields = {
            "speciality": spec,
            "urgency": "Routine",
            "reason": f"Pre-existing active {spec} referral (synthetic fixture).",
            "referrer_name": "Seed fixture",
            "referrer_org": p.get("gp_practice"),
            "status": "active",
            "source_id": f"SEED-{nhs}-{spec}",
            "suspected_cancer": False,
        }
        uuid, action = write_referral_idempotent(
            client, metadata, patient["uuid"], fields,
            encounter_datetime=_now_offset(days_ago=30),
        )
        if action == "created":
            created += 1
        else:
            exists += 1
        print(f"  {action.upper():<8} {nhs} {p['first_name']} {p['last_name']} "
              f"active:{spec} -> encounter {uuid}")

    print(f"\nSummary: created={created}, already-present={exists}, failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
