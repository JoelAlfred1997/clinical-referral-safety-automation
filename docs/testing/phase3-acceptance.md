# Phase 3 — Synthetic Referrals & Expected Outcomes: Acceptance Record

**Date:** 2026-06-09
**Result:** ✅ PASS — 15 synthetic referrals + 15 expected-outcome files created, covering all
required scenarios and all four bot decisions.

## Deliverable (per roadmap)
> Phase 3 | ≥15 synthetic referrals + expected-outcome files | **All scenarios + expected outcomes exist**

## What was built
- **15 referral inputs** in `data/input-referrals/` (`REF-001`…`REF-015`).
  - 14 are realistic synthetic GP referral letters (`.txt`); each carries a
    `SYNTHETIC TEST DATA — NOT A REAL PATIENT` banner.
  - `REF-015-corrupt.pdf` is a deliberately malformed PDF (truncated, no valid xref/`%%EOF`)
    to exercise the unreadable-file path.
- **15 expected-outcome files** in `data/expected-outcomes/` (`REF-NNN.expected.json`) — the
  test oracle for Phases 4–12 (expected extraction, missing fields, match result, safety flags,
  reason codes, bot decision, final status).
- **`data/expected-outcomes/README.md`** — schema + full scenario matrix + coverage summary.

Expected-outcome files are kept **outside** `data/input-referrals/` so the Phase 8 dispatcher
never mistakes an oracle file for a referral to ingest.

## Wiring to real seeded patients (from Phase 2)
Every referral targets a real seeded patient or a reserved no-match fixture:
- Clean exact: Bennett 9990000018, Davies 9990000034, Clarke 9990000026
- DOB mismatch: Ruby Shaw 9990000271 (letter DOB 1985-09-14 vs OpenMRS 1985-09-04)
- Partial: Leo Hamilton 9990000298 (no NHS number on letter; postcode discrepancy)
- Multiple candidates: Helen Walsh 9990000301 / 9990000328 (same name + DOB 1975-03-12, no NHS number)
- Duplicate: Arthur Reed 9990000336 (existing active Cardiology referral)
- Urgent 2WW cancer: Stanley Knight 9990000352
- Safeguarding/child: Florence Cole 9990000344 (DOB 2018)
- No match: Maria Fernandes 9990000360, Ibrahim Osei 9990000379 (reserved, not in OpenMRS)
- Incomplete: Daniel Owen 9990000166 (no speciality/priority/reason)
- Low confidence: Mia Roberts 9990000085 (garbled scan/fax)

## Acceptance checks (all PASS)
| Criterion | Evidence |
|---|---|
| ≥15 referrals exist | 15 files in `data/input-referrals/` (`REF-001`…`REF-015`) |
| Expected-outcome file per referral | 15 `*.expected.json`; all parse as valid JSON (`json.load` over all 15 → 0 invalid) |
| All match scenarios covered | exact, DOB-mismatch, partial, multiple-candidate, no-match, not-applicable |
| All four bot decisions covered | AUTO_CREATE ×3, HUMAN_REVIEW ×10, BUSINESS_EXCEPTION ×1, SYSTEM_EXCEPTION ×1 |
| All safety routing reasons covered | match-risk, duplicate, urgent/2WW, safeguarding/child, incomplete, low-confidence, not-a-referral, unreadable |
| Synthetic-by-construction | 999-range NHS numbers, Ofcom 07700 900xxx phones, synthetic banner on every letter |
| Referrals wired to real patients | Each `patient_ref` references a Phase 2 seeded patient (or reserved no-match) |

## Decision / status vocabulary established (feeds Phase 5)
- **match_result:** EXACT_MATCH · DOB_MISMATCH · PARTIAL_MATCH · MULTIPLE_CANDIDATES · NO_MATCH · NOT_APPLICABLE
- **bot_decision:** AUTO_CREATE_REFERRAL_RECORD · HUMAN_REVIEW_REQUIRED · BUSINESS_EXCEPTION · SYSTEM_EXCEPTION
- **final_status:** REFERRAL_CREATED_IN_OPENMRS · ROUTED_TO_HUMAN_REVIEW · BUSINESS_EXCEPTION_FAILED · SYSTEM_EXCEPTION_ESCALATED
- **reason codes:** MATCH_EXACT, MATCH_DOB_MISMATCH, MATCH_PARTIAL, MATCH_MULTIPLE_CANDIDATES,
  MATCH_NONE, DUPLICATE_REFERRAL, URGENT_RED_FLAG, SAFEGUARDING, CHILD_PATIENT,
  INCOMPLETE_MANDATORY_FIELDS, LOW_EXTRACTION_CONFIDENCE, NOT_A_REFERRAL, FILE_UNREADABLE

## Notes / deferred
- **REF-007 duplicate** depends on a pre-existing Cardiology Referral encounter for Arthur Reed,
  seeded in Phase 6/8 once the `Referral` encounter type/concepts exist. Tracked, not forgotten.
- A few `.txt` referrals may optionally be re-rendered as real `.pdf` in Phase 4 to exercise the
  PDF→text extraction path on valid PDFs (REF-015 already covers the corrupt-PDF path).

## Next: Phase 4
Build the extraction service (LLM + regex fallback + schema validation): each referral → valid
JSON; `missing_fields`, `confidence_score`, and safety flags computed and checked against these
`*.expected.json` oracles.
