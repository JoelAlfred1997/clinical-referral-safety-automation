#!/usr/bin/env python3
"""Phase 12 acceptance gate — the consolidated end-to-end test.

Re-derives the whole evidence pack from the real run artifacts + oracles and asserts the
Definition of Done is met for testing:

  1. all 15 synthetic referrals are present and tested,
  2. every bot decision matches its Phase 3 oracle (match_result, bot_decision, final),
  3. all four outcome classes are demonstrated with the expected counts (3/10/1/1),
  4. human-in-the-loop review changes the outcome (some approved-in, some rejected-out),
  5. the safety invariant holds — 0 referrals auto-created while carrying a safety flag,
  6. the run reconciles with the append-only audit log (every referral has an audit row),
  7. every prior phase acceptance record (phase1..11) is recorded as PASS,
  8. the generated evidence pack exists, carries the synthetic banner, and is consistent
     with the model (no stale hand edits).

Self-contained: reads only committed/regenerable artifacts; creates nothing.

ALL DATA IS SYNTHETIC. OpenMRS is a mock EPR/EMR.
"""

from __future__ import annotations

import os
import sys

import evidence_model as em
import build_evidence_pack as bep

_REPO_ROOT = em._REPO_ROOT
PACK = os.path.join(_REPO_ROOT, "docs", "testing", "evidence-pack.md")

EXPECTED_CLASS_COUNTS = {
    "Happy path (straight-through)": 3,
    "Human review": 10,
    "Business exception": 1,
    "System exception": 1,
}


def main() -> int:
    ev = em.build_evidence()
    rows = ev["rows"]
    checks: list[tuple[bool, str]] = []

    def check(ok: bool, msg: str) -> None:
        checks.append((bool(ok), msg))

    # 1. all 15 referrals present
    ids = [r["referral_id"] for r in rows]
    expected_ids = [f"REF-{n:03d}" for n in range(1, 16)]
    check(ids == expected_ids, f"all 15 referrals present and tested ({len(ids)} found)")

    # 2. every decision matches its oracle
    n_ok = ev["decisions_matching_oracle"]
    mismatches = [r["referral_id"] for r in rows if not r["decision_matches_oracle"]]
    check(n_ok == ev["total"] and not mismatches,
          f"every decision matches the Phase 3 oracle ({n_ok}/{ev['total']})"
          + (f" — mismatches: {mismatches}" if mismatches else ""))

    # 3. all four outcome classes demonstrated with expected counts
    counts = ev["outcome_classes"]
    class_ok = counts == EXPECTED_CLASS_COUNTS
    check(class_ok,
          "all four outcome classes demonstrated "
          f"(happy/review/BE/SE = "
          f"{counts.get('Happy path (straight-through)', 0)}/"
          f"{counts.get('Human review', 0)}/"
          f"{counts.get('Business exception', 0)}/"
          f"{counts.get('System exception', 0)})")

    # 4. human-in-the-loop changes the outcome (both directions)
    check(ev["hitl_created"] >= 1 and ev["hitl_rejected"] >= 1,
          f"human review changes the outcome: {ev['hitl_created']} approved-in, "
          f"{ev['hitl_rejected']} rejected-out of {ev['hitl_total']} reviewed")

    # 5. safety invariant
    flag = ev["kpis"]["auto_created_with_safety_flag"]
    check(flag == 0, f"safety invariant: {flag} referrals auto-created while carrying a safety flag")

    # 6. audit reconciliation — every referral has at least one audit row
    audit_refs = {a["referral_id"] for a in ev["audit_rows"]}
    missing_audit = [r["referral_id"] for r in rows if r["referral_id"] not in audit_refs]
    check(not missing_audit,
          f"every referral appears in the audit log ({len(ev['audit_rows'])} rows)"
          + (f" — missing: {missing_audit}" if missing_audit else ""))

    # 7. every prior phase acceptance record is PASS
    docs = ev["acceptance_docs"]
    not_pass = [d["phase"] for d in docs if not d["passed"]]
    check(not not_pass,
          f"all {len(docs)} prior phase acceptance records are PASS"
          + (f" — failing: {not_pass}" if not_pass else ""))

    # 8. the generated evidence pack is present, banner-carrying, and consistent
    pack_ok = os.path.exists(PACK)
    banner_ok = consistent = False
    if pack_ok:
        with open(PACK, encoding="utf-8") as fh:
            text = fh.read()
        banner_ok = ("synthetic" in text.lower()) and ("Not a live NHS system" in text)
        # regenerate from the model and compare — fails if the committed pack was hand-edited
        consistent = (text.strip() == bep.render(ev).strip())
    check(pack_ok and banner_ok and consistent,
          "generated evidence pack exists, carries the synthetic banner, and matches the model"
          + ("" if pack_ok else " — MISSING; run build_evidence_pack.py")
          + ("" if (not pack_ok or consistent) else " — STALE; regenerate it"))

    # ---- report ----
    passed = sum(1 for ok, _ in checks if ok)
    for ok, msg in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {msg}")
    print(f"{passed}/{len(checks)} checks passed")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
