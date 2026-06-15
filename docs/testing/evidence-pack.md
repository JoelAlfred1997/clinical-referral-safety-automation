# Evidence Pack — Clinical Referral Safety Automation (Phase 12)

> ⚠️ **Portfolio simulation — 100% synthetic data. Not a live NHS system.** OpenMRS is a mock EPR/EMR. AI assists extraction only; deterministic rules and human reviewers own every safety outcome.

**This document is generated** by `services/testing/build_evidence_pack.py` from the test oracles (`data/expected-outcomes/`), the bot's real decision artifacts (`data/decisions/`) and the post-review resolution (Phase 9). No figure below is hand-typed. Regenerate after any run; the Phase 12 gate (`services/testing/validate_acceptance.py`) re-derives and checks every claim.

## 1. Consolidated build status

All **11** prior phase acceptance gates are recorded as PASS (**11/11**). Phase 12 consolidates them into this pack.

| Phase | Deliverable | Acceptance record | Result |
|---|---|---|---|
| 1 | OpenMRS local setup | [`phase1-acceptance.md`](phase1-acceptance.md) | ✅ PASS |
| 2 | Synthetic patient data | [`phase2-acceptance.md`](phase2-acceptance.md) | ✅ PASS |
| 3 | Synthetic referrals + oracles | [`phase3-acceptance.md`](phase3-acceptance.md) | ✅ PASS |
| 4 | Extraction service | [`phase4-acceptance.md`](phase4-acceptance.md) | ✅ PASS |
| 5 | Rules & safety decision engine | [`phase5-acceptance.md`](phase5-acceptance.md) | ✅ PASS |
| 6 | OpenMRS workflow mapping | [`phase6-acceptance.md`](phase6-acceptance.md) | ✅ PASS |
| 7 | REFramework design spec | [`phase7-acceptance.md`](phase7-acceptance.md) | ✅ PASS |
| 8 | UiPath build (live run) | [`phase8-acceptance.md`](phase8-acceptance.md) | ✅ PASS |
| 9 | Human-in-the-loop review | [`phase9-acceptance.md`](phase9-acceptance.md) | ✅ PASS |
| 10 | Reporting + dashboard | [`phase10-acceptance.md`](phase10-acceptance.md) | ✅ PASS |
| 11 | Clinical safety + IG docs | [`phase11-acceptance.md`](phase11-acceptance.md) | ✅ PASS |
| 12 | Testing + evidence pack (this) | `phase12-acceptance.md` | see §5 |

## 2. Headline figures (from the real Phase 8 + Phase 9 run)

| Metric | Value |
|---|---|
| Referrals tested end-to-end | 15 |
| Decisions matching the oracle | 15/15 |
| Created in OpenMRS | 9 (3 automated + 6 human-approved/amended) |
| Routed to human review | 10 (67%) |
| Rejected at review (no record) | 4 |
| Exceptions (business + system) | 2 |
| **Auto-created while carrying a safety flag** | **0** — the core safety guarantee |
| Audit rows (who/what/before/after/when/why) | 25 |

## 3. The four outcome classes — all demonstrated

Definition of Done item 7 requires happy-path, human-review, business-exception and system-exception outcomes to be distinct and demonstrated:

| Outcome class | Referrals | Count |
|---|---|---|
| Happy path (straight-through) | REF-001, REF-002, REF-003 | 3 |
| Human review | REF-004, REF-005, REF-006, REF-007, REF-008, REF-009, REF-010, REF-011, REF-012, REF-013 | 10 |
| Business exception | REF-014 | 1 |
| System exception | REF-015 | 1 |

Human-in-the-loop changed the outcome (DoD item 5): of 10 reviewed referrals, **6** were approved/amended into OpenMRS and **4** were rejected with no record created.

## 4. Traceability matrix — all 15 scenarios (expected vs actual)

Expected values are the Phase 3 oracle; actual values are the bot's real decision artifact. The final column is the outcome after the recorded human-review decision.

| Ref | Scenario | Outcome class | Match (exp→act) | Decision (exp→act) | Reason codes | Oracle? | Human-resolved outcome |
|---|---|---|---|---|---|---|---|
| REF-001 | exact_match_clean | Happy path (straight-through) | EXACT_MATCH | AUTO_CREATE_REFERRAL_RECORD | MATCH_EXACT | ✅ | Created in OpenMRS |
| REF-002 | exact_match_clean | Happy path (straight-through) | EXACT_MATCH | AUTO_CREATE_REFERRAL_RECORD | MATCH_EXACT | ✅ | Created in OpenMRS |
| REF-003 | exact_match_clean | Happy path (straight-through) | EXACT_MATCH | AUTO_CREATE_REFERRAL_RECORD | MATCH_EXACT | ✅ | Created in OpenMRS |
| REF-004 | dob_mismatch | Human review | DOB_MISMATCH | HUMAN_REVIEW_REQUIRED | MATCH_DOB_MISMATCH | ✅ | Created in OpenMRS (APPROVE) |
| REF-005 | partial_match | Human review | PARTIAL_MATCH | HUMAN_REVIEW_REQUIRED | MATCH_PARTIAL | ✅ | Created in OpenMRS (APPROVE) |
| REF-006 | multiple_candidates | Human review | MULTIPLE_CANDIDATES | HUMAN_REVIEW_REQUIRED | MATCH_MULTIPLE_CANDIDATES | ✅ | Created in OpenMRS (APPROVE) |
| REF-007 | duplicate_referral | Human review | EXACT_MATCH | HUMAN_REVIEW_REQUIRED | MATCH_EXACT, DUPLICATE_REFERRAL | ✅ | Rejected at review (no record) (REJECT) |
| REF-008 | urgent_2ww_suspected_cancer | Human review | EXACT_MATCH | HUMAN_REVIEW_REQUIRED | MATCH_EXACT, URGENT_RED_FLAG | ✅ | Created in OpenMRS (APPROVE) |
| REF-009 | safeguarding_child | Human review | EXACT_MATCH | HUMAN_REVIEW_REQUIRED | MATCH_EXACT, URGENT_RED_FLAG, SAFEGUARDING, CHILD_PATIENT | ✅ | Created in OpenMRS (APPROVE) |
| REF-010 | no_match | Human review | NO_MATCH | HUMAN_REVIEW_REQUIRED | MATCH_NONE | ✅ | Rejected at review (no record) (REJECT) |
| REF-011 | no_match | Human review | NO_MATCH | HUMAN_REVIEW_REQUIRED | MATCH_NONE | ✅ | Rejected at review (no record) (REJECT) |
| REF-012 | incomplete_mandatory_fields | Human review | EXACT_MATCH | HUMAN_REVIEW_REQUIRED | MATCH_EXACT, INCOMPLETE_MANDATORY_FIELDS | ✅ | Rejected at review (no record) (REJECT) |
| REF-013 | low_extraction_confidence | Human review | EXACT_MATCH | HUMAN_REVIEW_REQUIRED | MATCH_EXACT, INCOMPLETE_MANDATORY_FIELDS, LOW_EXTRACTION_CONFIDENCE | ✅ | Created in OpenMRS (AMEND) |
| REF-014 | business_exception_not_a_referral | Business exception | NOT_APPLICABLE | BUSINESS_EXCEPTION | NOT_A_REFERRAL | ✅ | Business exception |
| REF-015 | system_exception_unreadable_file | System exception | NOT_APPLICABLE | SYSTEM_EXCEPTION | FILE_UNREADABLE | ✅ | System exception |

**Evidence per row:** `data/extracted-json/REF-NNN.extracted.json` (extraction), `data/decisions/REF-NNN.decision.json` (decision), `data/expected-outcomes/REF-NNN.expected.json` (oracle), and the append-only `data/audit/audit-log.csv` (one row per system action). The Phase 10 workbook `reports/referral-safety-report.xlsx` and `reports/dashboard.html` visualise the same data.

## 5. Phase 12 acceptance gate

Run `python services/testing/validate_acceptance.py`. It re-derives this entire pack from the artifacts and asserts: all 15 referrals present, every decision matches its oracle, all four outcome classes demonstrated, human review changes the outcome, the safety invariant holds (0 unsafe auto-creates), the run reconciles with the audit log, every prior phase acceptance record is PASS, and this generated pack is internally consistent. See `docs/testing/phase12-acceptance.md` for the recorded result.

---
*Generated from oracles + real decision artifacts + post-review resolution. All data synthetic.*
