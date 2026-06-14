#!/usr/bin/env python3
"""Reset OpenMRS referral state to the Phase 5/6 BASELINE for a clean Phase 8 run.

Baseline = the ONLY pre-existing active referral is Arthur Reed's Cardiology one
(the REF-007 duplicate-target). Every other Referral encounter is voided, so the
AUTO_CREATE referrals (Bennett/Davies/Clarke) are created fresh by the Phase 8
bot and verify cleanly, and the decision engine (source=openmrs) sees no stale
duplicates.

What it does:
  1. voids every non-voided Referral encounter for all synthetic patients;
  2. re-seeds Reed's pre-existing active Cardiology referral (seed_existing_referrals).

Usage:  python reset_openmrs_baseline.py        (needs OpenMRS running + metadata setup)

ALL DATA IS SYNTHETIC. OpenMRS is a mock EPR/EMR.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.metadata import load_metadata  # noqa: E402
from src.openmrs_client import OpenmrsClient  # noqa: E402
from src.referral_writer import get_referral_encounters  # noqa: E402

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_PATIENTS = os.path.join(_REPO_ROOT, "data", "synthetic-patients", "synthetic_patients.json")


def _void_encounter(client: OpenmrsClient, uuid: str) -> None:
    req = urllib.request.Request(
        f"{client.rest}/encounter/{uuid}?reason=Phase8+baseline+reset",
        method="DELETE",
    )
    req.add_header("Authorization", client._auth)
    with urllib.request.urlopen(req, timeout=40):
        pass


def main() -> int:
    client = OpenmrsClient()
    if not client.session_authenticated():
        print(f"OpenMRS not ready / not authenticated at {client.rest}.")
        return 1
    metadata = load_metadata()
    patients = json.load(open(_PATIENTS, encoding="utf-8"))

    voided = 0
    for p in patients:
        nhs = p.get("nhs_number")
        patient = client.find_patient_by_nhs(nhs) if nhs else None
        if not patient:
            continue
        for enc in get_referral_encounters(client, metadata, patient["uuid"]):
            _void_encounter(client, enc["uuid"])
            voided += 1
            print(f"  voided {enc['uuid']}  ({nhs}  {enc['fields'].get('source_id')}:"
                  f"{enc['fields'].get('speciality')})")
    print(f"Voided {voided} referral encounter(s).")

    # Re-seed Reed's pre-existing active Cardiology referral (the REF-007 dup target).
    print("Re-seeding the pre-existing duplicate target...")
    import seed_existing_referrals  # noqa: E402  (its main() seeds Reed)
    rc = seed_existing_referrals.main()
    print("Baseline ready: only the seeded duplicate target is active.")
    return rc or 0


if __name__ == "__main__":
    raise SystemExit(main())
