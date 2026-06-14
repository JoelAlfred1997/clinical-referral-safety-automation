#!/usr/bin/env python3
"""Resolve human-reviewed referrals — the bot re-reads each clinician decision
and *changes the final outcome* (Phase 9).

For every review that a clinician has DECIDED (and any earlier FAILED attempt):

  REJECT  -> no OpenMRS record; final_status = REVIEW_REJECTED_NO_RECORD.
  APPROVE -> create the referral in OpenMRS via the writeback service (:8091),
             using the identity the reviewer confirmed;
             final_status = REFERRAL_CREATED_IN_OPENMRS.
  AMEND   -> apply the reviewer's corrected fields, then create as for APPROVE.

Every outcome appends a row to the append-only audit log
(`data/audit/audit-log.csv`). The pass is idempotent: RESOLVED rows are skipped,
and the writeback itself is keyed on REF-NNN, so a re-run returns "exists" rather
than creating a duplicate OpenMRS record.

This is the same service-oriented pattern the Phase 8 performer uses: the bot
orchestrates; the escaping-sensitive OpenMRS write stays in the proven Phase 6
writer behind the /writeback HTTP service.

ALL DATA IS SYNTHETIC. OpenMRS is a mock EPR/EMR.

Usage:
    python resolve_reviews.py            # resolve all decided reviews
    python resolve_reviews.py --dry-run  # show what would happen, change nothing
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import review_store as store  # noqa: E402

_REPO_ROOT = store._REPO_ROOT
AUDIT_LOG = os.path.join(_REPO_ROOT, "data", "audit", "audit-log.csv")
WRITEBACK_URL = os.getenv("WRITEBACK_SERVICE_URL", "http://localhost:8091/writeback")
AUTO_CREATE = "AUTO_CREATE_REFERRAL_RECORD"

# Reviewer amend keys map straight onto the Phase 4 extraction field names.
_AMENDABLE = {
    "specialty", "priority", "reason_for_referral", "referring_clinician",
    "referring_practice", "patient_nhs_number",
}


def _load_json(path: str) -> dict:
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _audit(ref_id: str, action: str, status: str, match_result: str, detail: str) -> None:
    os.makedirs(os.path.dirname(AUDIT_LOG), exist_ok=True)
    row = [store.utcnow(), ref_id, action, status, match_result or "", detail]
    with open(AUDIT_LOG, "a", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerow(row)


def _build_writeback_payload(review: dict) -> tuple[dict, dict]:
    """Reconstruct the extraction + decision the writeback service expects,
    overlaying the reviewer's confirmed identity and any amended fields."""
    ref_id = review["referral_id"]
    extraction = _load_json(
        os.path.join(_REPO_ROOT, "data", "extracted-json", f"{ref_id}.extracted.json"))
    decision = _load_json(
        os.path.join(_REPO_ROOT, "data", "decisions", f"{ref_id}.decision.json"))

    # Apply reviewer amendments to the extracted referral fields.
    ex = extraction.setdefault("extraction", {})
    for key, value in (review.get("amended_fields") or {}).items():
        if key in _AMENDABLE:
            ex[key] = value

    # The human approval turns this into an authorised create.
    decision["bot_decision"] = AUTO_CREATE

    # Pin the identity the reviewer confirmed (mandatory when the bot could not
    # safely match: partial / multiple-candidate / no original NHS number).
    nhs = (review.get("confirmed_nhs_number")
           or (decision.get("matched_patient") or {}).get("nhs_number")
           or ex.get("patient_nhs_number"))
    if not nhs:
        raise store.ReviewError(
            f"{ref_id}: approval needs a confirmed NHS number (reviewer must select the patient)")
    mp = decision.get("matched_patient") or {}
    mp = {**mp, "nhs_number": nhs,
          "first_name": mp.get("first_name") or ex.get("patient_first_name"),
          "last_name": mp.get("last_name") or ex.get("patient_last_name"),
          "source": "reviewer_confirmed"}
    decision["matched_patient"] = mp
    decision["referral_id"] = ref_id
    return extraction, decision


def _post_writeback(extraction: dict, decision: dict) -> tuple[int, dict]:
    body = json.dumps({"extraction": extraction, "decision": decision}).encode("utf-8")
    req = urllib.request.Request(WRITEBACK_URL, data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except ValueError:
            payload = {"error": str(exc)}
        return exc.code, payload


def resolve_one(conn, review: dict, *, dry_run: bool = False) -> dict:
    ref_id = review["referral_id"]
    decision = (review.get("reviewer_decision") or "").upper()
    reviewer = review.get("reviewer") or "?"
    match_result = review.get("match_result") or ""

    if decision == store.REJECT:
        if dry_run:
            return {"referral_id": ref_id, "action": "REJECT", "would": store.FINAL_REJECTED}
        store.mark_resolved(conn, ref_id, final_status=store.FINAL_REJECTED)
        _audit(ref_id, "REVIEW_RESOLVED_REJECT", store.FINAL_REJECTED, match_result,
               f"reviewer={reviewer};rationale={(review.get('rationale') or '')[:120]}")
        return {"referral_id": ref_id, "action": "REJECT", "final_status": store.FINAL_REJECTED}

    # APPROVE or AMEND -> create in OpenMRS.
    extraction, wb_decision = _build_writeback_payload(review)
    if dry_run:
        return {"referral_id": ref_id, "action": decision,
                "would": store.FINAL_CREATED,
                "nhs_number": wb_decision["matched_patient"]["nhs_number"]}

    code, payload = _post_writeback(extraction, wb_decision)
    if code == 200 and payload.get("verified"):
        enc = payload.get("encounter_uuid")
        store.mark_resolved(conn, ref_id, final_status=store.FINAL_CREATED, encounter_uuid=enc)
        _audit(ref_id, f"REVIEW_RESOLVED_{decision}", store.FINAL_CREATED, match_result,
               f"reviewer={reviewer};nhs={wb_decision['matched_patient']['nhs_number']};"
               f"encounter={enc};writeback={payload.get('action')}")
        return {"referral_id": ref_id, "action": decision,
                "final_status": store.FINAL_CREATED, "encounter_uuid": enc,
                "writeback_action": payload.get("action")}

    # Anything else is a system/operational fault: stays actionable for re-run.
    detail = f"reviewer={reviewer};http={code};error={str(payload.get('error'))[:140]}"
    store.mark_failed(conn, ref_id, final_status=store.FINAL_FAILED)
    _audit(ref_id, "REVIEW_RESOLUTION_FAILED", store.FINAL_FAILED, match_result, detail)
    return {"referral_id": ref_id, "action": decision, "final_status": store.FINAL_FAILED,
            "http": code, "error": payload.get("error")}


def resolve(conn, *, dry_run: bool = False) -> dict:
    """Resolve every decided/failed review. Idempotent: RESOLVED rows are skipped."""
    actionable = [r for r in store.list_reviews(conn)
                  if r["review_status"] in (store.DECIDED, store.FAILED)]
    results = []
    for review in actionable:
        try:
            results.append(resolve_one(conn, review, dry_run=dry_run))
        except store.ReviewError as exc:
            ref_id = review["referral_id"]
            if not dry_run:
                store.mark_failed(conn, ref_id, final_status=store.FINAL_FAILED)
                _audit(ref_id, "REVIEW_RESOLUTION_FAILED", store.FINAL_FAILED,
                       review.get("match_result") or "", f"error={exc}")
            results.append({"referral_id": ref_id, "action": "ERROR", "error": str(exc)})

    def outcome(r):  # live runs report final_status; dry-runs report "would"
        return r.get("final_status") or r.get("would")

    created = sum(1 for r in results if outcome(r) == store.FINAL_CREATED)
    rejected = sum(1 for r in results if outcome(r) == store.FINAL_REJECTED)
    failed = sum(1 for r in results if outcome(r) == store.FINAL_FAILED
                 or r.get("action") == "ERROR")
    return {
        "dry_run": dry_run,
        "actioned": len(results),
        "created_in_openmrs": created,
        "rejected_no_record": rejected,
        "failed": failed,
        "pending_remaining": len(store.list_reviews(conn, store.PENDING)),
        "results": results,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Resolve human-reviewed referrals (Phase 9).")
    ap.add_argument("--db", default=store.DEFAULT_DB_PATH)
    ap.add_argument("--dry-run", action="store_true", help="show outcomes, change nothing")
    args = ap.parse_args()

    conn = store.connect(args.db)
    summary = resolve(conn, dry_run=args.dry_run)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
