#!/usr/bin/env python3
"""Phase 9 acceptance gate — the human-in-the-loop loop, end to end.

Self-contained and reproducible: it uses its own throwaway SQLite store, ingests
the 10 referrals the Phase 8 bot routed to review, scripts a realistic clinician
worklist (approve / reject / amend), then runs the resolver and asserts that the
human decisions *changed the final outcome* — approvals/amends created verified
records in OpenMRS, rejections created none — and that a second pass is idempotent
(no duplicate OpenMRS records).

Requires: OpenMRS up, writeback service (:8091) running.  ALL DATA IS SYNTHETIC.

    python validate_acceptance.py
"""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import review_store as store  # noqa: E402
import resolve_reviews  # noqa: E402

# The scripted clinician worklist (the human-in-the-loop decisions under test).
SCENARIO = [
    ("REF-004", "Dr A Okonkwo", store.APPROVE, "9990000271", None, store.FINAL_CREATED),
    ("REF-005", "Dr A Okonkwo", store.APPROVE, "9990000298", None, store.FINAL_CREATED),
    ("REF-006", "Dr A Okonkwo", store.APPROVE, "9990000301", None, store.FINAL_CREATED),
    ("REF-007", "Dr A Okonkwo", store.REJECT, None, None, store.FINAL_REJECTED),
    ("REF-008", "Dr R Mensah", store.APPROVE, None, None, store.FINAL_CREATED),
    ("REF-009", "Dr R Mensah", store.APPROVE, None, None, store.FINAL_CREATED),
    ("REF-010", "Dr R Mensah", store.REJECT, None, None, store.FINAL_REJECTED),
    ("REF-011", "Dr R Mensah", store.REJECT, None, None, store.FINAL_REJECTED),
    ("REF-012", "Dr A Okonkwo", store.REJECT, None, None, store.FINAL_REJECTED),
    ("REF-013", "Dr A Okonkwo", store.AMEND, None,
     {"specialty": "Dermatology", "priority": "Routine",
      "reason_for_referral": "Suspicious changing pigmented lesion on the left forearm; "
      "please assess. (Fields confirmed with GP after re-reading the degraded fax.)"},
     store.FINAL_CREATED),
]

PASS, FAIL = "PASS", "FAIL"
results: list[tuple[str, str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((PASS if ok else FAIL, name, detail))


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="phase9-accept-")
    db = os.path.join(tmp, "review-store.sqlite")
    conn = store.connect(db)

    ing = store.ingest_csv(conn)
    check("ingest: 10 PENDING reviews loaded from Phase 8 CSV",
          ing["inserted"] == 10 and store.counts(conn).get(store.PENDING) == 10,
          f"inserted={ing['inserted']} counts={store.counts(conn)}")

    expected = {ref: final for ref, *_, final in SCENARIO}
    for ref, reviewer, decision, nhs, amend, _final in SCENARIO:
        store.record_decision(conn, ref, reviewer=reviewer, decision=decision,
                              rationale=f"acceptance: {decision.lower()} {ref}",
                              confirmed_nhs_number=nhs, amended_fields=amend)
    check("decisions: all 10 reviews DECIDED, mandatory who/why captured",
          store.counts(conn).get(store.DECIDED) == 10)

    # A decision without a rationale must be rejected (auditability is enforced).
    bad = False
    try:
        store.record_decision(conn, "REF-004", reviewer="x", decision=store.APPROVE, rationale="")
    except store.ReviewError:
        bad = True
    check("guard: a decision with no rationale is refused", bad)

    # The bot re-reads and applies the decisions.
    summary = resolve_reviews.resolve(conn)
    check("resolve: 6 created in OpenMRS, 4 rejected, 0 failed",
          summary["created_in_openmrs"] == 6 and summary["rejected_no_record"] == 4
          and summary["failed"] == 0, str({k: summary[k] for k in
          ("created_in_openmrs", "rejected_no_record", "failed")}))

    # Every outcome matches the clinician's decision, and approvals carry a
    # verified OpenMRS encounter (the decision genuinely changed the outcome).
    all_match, enc_ok = True, True
    for ref, final in expected.items():
        row = store.get(conn, ref)
        if row["review_status"] != store.RESOLVED or row["final_status"] != final:
            all_match = False
        if final == store.FINAL_CREATED and not row["encounter_uuid"]:
            enc_ok = False
    check("outcomes: every final_status matches the recorded decision", all_match)
    check("creates: each approved/amended referral has an OpenMRS encounter_uuid", enc_ok)
    check("no work left: 0 PENDING remain", store.counts(conn).get(store.PENDING, 0) == 0)

    # Idempotency: re-resolving changes nothing and creates no duplicate records.
    again = resolve_reviews.resolve(conn)
    check("idempotent: a second resolve actions 0 reviews (all RESOLVED)",
          again["actioned"] == 0, f"actioned={again['actioned']}")

    npass = sum(1 for r in results if r[0] == PASS)
    print("\nPhase 9 — Human-in-the-loop review: acceptance gate\n" + "=" * 55)
    for status, name, detail in results:
        print(f"[{status}] {name}" + (f"  ({detail})" if detail and status == FAIL else ""))
    print("=" * 55)
    print(f"{npass}/{len(results)} checks passed")
    print(f"(throwaway store: {db})")
    return 0 if npass == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
