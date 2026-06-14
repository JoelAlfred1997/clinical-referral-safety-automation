# Phase 9 — Human-in-the-Loop Review: Acceptance Record

**Date:** 2026-06-15
**Result:** ✅ PASS — the 10 referrals the Phase 8 bot routed to human review now live
in a **real review store** (SQLite). A clinician's decision (**APPROVE / REJECT / AMEND**,
with their identity and a rationale) was recorded against each, and a **UiPath
ReviewResolver process** re-read those decisions and **changed the final outcome**:
**6 referrals were created in OpenMRS** (verified by re-read) and **4 were rejected with
no record**. Every action is **audited**, and re-running is **idempotent** (no duplicate
records). Self-contained gate: **8/8**.

This delivers Definition-of-Done item **5** — *"A human review decision can be recorded
and changes the final outcome"* — and strengthens items 4 and 6.

## What was built

- **`services/review-service/`** — the review store and the loop (stdlib only: `sqlite3`,
  `http.server`, `urllib`):
  - **`src/review_store.py`** — SQLite store at `data/review/review-store.sqlite`. One row
    per referral with the lifecycle `PENDING → DECIDED → RESOLVED` (or `FAILED`). The row
    *is* the human-decision audit trail: `reviewer`, `reviewer_decision`, `rationale`,
    `confirmed_nhs_number`, `amended_fields`, `final_status`, `encounter_uuid`, and
    routed/created/decided/resolved timestamps (who / what / before / after / when / why).
  - **`init_store.py`** — idempotently ingests the Phase 8 `review-store.csv` (10 PENDING).
  - **`record_decision.py`** — **the reviewer action.** APPROVE / REJECT / AMEND with a
    mandatory reviewer identity and rationale; does not touch OpenMRS.
  - **`resolve_reviews.py`** — **the bot re-read.** Applies each decision: APPROVE/AMEND →
    create in OpenMRS via the writeback service (`:8091`); REJECT → no record. Writes an
    audit row per outcome. Idempotent.
  - **`app.py`** — HTTP service on `:8092` (`/health`, `/reviews`, `/reviews/<id>/decision`,
    `/resolve`) so the UiPath process can drive it, exactly like the other three services.
  - **`validate_acceptance.py`** — the self-contained Phase 9 gate (8 checks).
- **`uipath/NHS.ReferralSafety.ReviewResolver/`** — a UiPath **Process** (Windows / VB,
  `UiPath.WebAPI.Activities`). `Main.xaml`: **POST `/resolve`** → guard non-200 (system
  throw) → **Deserialize JSON** → log `created / rejected / failed` → guard `failed > 0`
  (system throw). The same service-oriented pattern as the Phase 8 performer.

## The reviewer worklist (recorded decisions)

| Referral | Why it was in review (Phase 8) | Clinician decision | Outcome |
|---|---|---|---|
| REF-004 Shaw | DOB mismatch (wrong-patient risk) | **APPROVE** — PAS confirms NHS 9990000271; referral DOB was a typo | Created in OpenMRS |
| REF-005 Hamilton | Partial match (no NHS number) | **APPROVE** — single EPR patient, identity confirmed | Created in OpenMRS |
| REF-006 Walsh | Multiple candidates | **APPROVE** — disambiguated to NHS 9990000301 | Created in OpenMRS |
| REF-007 Reed | Duplicate (active Cardiology referral) | **REJECT** — genuine duplicate, return to GP | **No record** |
| REF-008 Knight | 2WW suspected cancer (urgent) | **APPROVE** — expedited, identity exact-matched | Created in OpenMRS |
| REF-009 Cole | Safeguarding / child patient | **APPROVE** — safeguarding flagged to lead; referral valid | Created in OpenMRS |
| REF-010 Fernandes | No match in EPR | **REJECT** — not registered, return to referrer | **No record** |
| REF-011 Osei | No match in EPR | **REJECT** — not registered, return to referrer | **No record** |
| REF-012 Owen | Incomplete mandatory fields | **REJECT** — missing clinical detail, return to GP | **No record** |
| REF-013 Roberts | Low-confidence degraded fax; missing fields | **AMEND** — reviewer supplied specialty=Dermatology, priority=Routine, reason; then create | Created in OpenMRS |

**Decisions changed the outcome:** 6 referrals the bot was *not* allowed to auto-create were
created after a human approved/completed them; 4 were explicitly closed without a record by
human judgement. The AMEND (REF-013) shows the human supplying the very fields the bot left
blank — re-read from OpenMRS afterwards:

```
encounter 5adbe442-0b07-4ad2-9163-06d81e970f33
  Referral - Speciality: Dermatology         (was null — degraded scan)
  Referral - Urgency: Routine                (was null)
  Referral - Reason: Suspicious changing pigmented lesion on the left forearm; please assess. …
  Referral - Source Document ID: REF-013
  Referral - Status: active
```

## Live run (UiPath ReviewResolver)

```
[Information] ReviewResolver started. The bot re-reads clinician decisions via http://localhost:8092/resolve
[Information] Resolved 10 review(s): 6 created in OpenMRS, 4 rejected (no record), 0 failed.
[Information] ReviewResolver finished. Pending reviews remaining: 0
... execution ended in: 00:00:19   Result: Success
```

Store after the run: **10 RESOLVED** (6 `REFERRAL_CREATED_IN_OPENMRS` with an
`encounter_uuid`, 4 `REVIEW_REJECTED_NO_RECORD`). The append-only audit log
(`data/audit/audit-log.csv`) gained 10 `REVIEW_RESOLVED_{APPROVE|AMEND|REJECT}` rows
carrying the reviewer, the confirmed NHS number + encounter UUID (creates) or the rationale
(rejections) — the full before→after trail alongside the original Phase 8 routing rows.

## Idempotency (re-run is safe)

Re-running the UiPath ReviewResolver (`--skip-build`):

```
[Information] Resolved 0 review(s): 0 created in OpenMRS, 0 rejected (no record), 0 failed.
[Information] ReviewResolver finished. Pending reviews remaining: 0
```

Already-`RESOLVED` reviews are skipped, and the writeback is keyed on the `REF-NNN` source-id
obs, so no duplicate OpenMRS record is ever created.

## Acceptance gate (self-contained, reproducible)

`python services/review-service/validate_acceptance.py` — own throwaway store, scripts the
worklist, resolves against the live writeback service, asserts the loop:

```
[PASS] ingest: 10 PENDING reviews loaded from Phase 8 CSV
[PASS] decisions: all 10 reviews DECIDED, mandatory who/why captured
[PASS] guard: a decision with no rationale is refused
[PASS] resolve: 6 created in OpenMRS, 4 rejected, 0 failed
[PASS] outcomes: every final_status matches the recorded decision
[PASS] creates: each approved/amended referral has an OpenMRS encounter_uuid
[PASS] no work left: 0 PENDING remain
[PASS] idempotent: a second resolve actions 0 reviews (all RESOLVED)
8/8 checks passed
```

## How to reproduce

```bash
# services: writeback (8091) + review (8092) running; OpenMRS up
cd services/review-service
python init_store.py                                   # 10 PENDING from the Phase 8 CSV
# record the worklist (see the table above; record_decision.py --help for syntax)
python record_decision.py REF-005 --reviewer "Dr A Okonkwo" --approve --nhs 9990000298 \
    --rationale "Identity confirmed against PAS; safe to create."
#   ... (REF-004/006/008/009 approve, REF-007/010/011/012 reject, REF-013 amend) ...
# the bot applies them, via UiPath:
export PATH="/c/Program Files/dotnet:$PATH"
cd ../../uipath/NHS.ReferralSafety.ReviewResolver && uip rpa run --file-path Main.xaml
# verify + idempotency:
uip rpa run --file-path Main.xaml --skip-build         # resolves 0
```

## Screenshots to capture (portfolio)

- The OpenMRS SPA showing one review-created referral (e.g. Mia Roberts' **Dermatology**
  referral — the amended one).
- `data/audit/audit-log.csv` showing the original `HUMAN_REVIEW_REQUIRED` rows **and** the
  matching `REVIEW_RESOLVED_*` rows (before → after).
- The ReviewResolver run log (`6 created in OpenMRS, 4 rejected`).
- A `SELECT referral_id, review_status, reviewer_decision, final_status, reviewer FROM reviews`
  dump of the SQLite store.

## Scope boundary (what Phase 9 does NOT do)

The reviewer is driven by a CLI / REST call standing in for a clinician working a worklist —
this is a portfolio simulation, not a clinical review UI. What is **real**: the SQLite store,
the enforced who/why audit, the `PENDING → DECIDED → RESOLVED` state machine, and the OpenMRS
create/verify via the proven Phase 6 writer. Reporting and a dashboard over this run are
**Phase 10**.

## Next — Phase 10

Reporting + dashboard over the real Phase 8 + Phase 9 data (auto-created, routed-to-review,
reviewer outcomes, exceptions) with portfolio screenshots.
