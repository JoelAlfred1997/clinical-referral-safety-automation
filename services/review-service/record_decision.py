#!/usr/bin/env python3
"""Record a clinician's review decision (the human-in-the-loop action, Phase 9).

This stands in for a reviewer working a worklist in a clinical system: it writes
their decision — APPROVE, REJECT, or AMEND — onto a PENDING referral, together
with their identity and a rationale (the auditable "who" and "why"). It does NOT
touch OpenMRS; applying the decision is the bot's job (resolve_reviews.py), which
keeps the human decision and the system action cleanly separated and auditable.

Examples:
    # Approve a partial-match referral, confirming the patient's identity:
    python record_decision.py REF-005 --reviewer "Dr A Okonkwo" --approve \
        --nhs 9990000298 \
        --rationale "Name+DOB confirmed against PAS; single patient. Safe to create."

    # Reject a genuine duplicate (no new record):
    python record_decision.py REF-007 --reviewer "Dr A Okonkwo" --reject \
        --rationale "Active Cardiology referral already exists; duplicate, return to GP."

    # Amend a degraded-scan referral (fill the missing fields) then create:
    python record_decision.py REF-013 --reviewer "Dr A Okonkwo" --amend \
        --set specialty=Dermatology --set priority=Routine \
        --set reason_for_referral="Suspicious pigmented lesion left forearm; please assess." \
        --rationale "Re-read the fax with the GP; fields confirmed."

ALL DATA IS SYNTHETIC.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import review_store as store  # noqa: E402


def _parse_set(pairs: list[str]) -> dict:
    out: dict[str, str] = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise SystemExit(f"--set expects field=value, got {pair!r}")
        key, value = pair.split("=", 1)
        out[key.strip()] = value
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Record a clinician review decision (Phase 9).")
    ap.add_argument("referral_id")
    ap.add_argument("--reviewer", required=True, help="the clinician's name/identity")
    ap.add_argument("--rationale", required=True, help="why (recorded for audit)")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--approve", action="store_const", dest="decision", const=store.APPROVE)
    group.add_argument("--reject", action="store_const", dest="decision", const=store.REJECT)
    group.add_argument("--amend", action="store_const", dest="decision", const=store.AMEND)
    ap.add_argument("--nhs", dest="nhs", help="confirmed NHS number (approvals)")
    ap.add_argument("--set", dest="amend", action="append", default=[],
                    help="amended field=value (repeatable; AMEND only)")
    ap.add_argument("--db", default=store.DEFAULT_DB_PATH)
    args = ap.parse_args()

    amended = _parse_set(args.amend)
    conn = store.connect(args.db)
    try:
        row = store.record_decision(
            conn, args.referral_id, reviewer=args.reviewer, decision=args.decision,
            rationale=args.rationale, confirmed_nhs_number=args.nhs,
            amended_fields=amended or None)
    except store.ReviewError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(json.dumps({
        "referral_id": row["referral_id"],
        "review_status": row["review_status"],
        "reviewer_decision": row["reviewer_decision"],
        "reviewer": row["reviewer"],
        "confirmed_nhs_number": row["confirmed_nhs_number"],
        "amended_fields": row["amended_fields"],
        "decided_utc": row["decided_utc"],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
