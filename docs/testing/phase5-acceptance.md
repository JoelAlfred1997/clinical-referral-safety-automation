# Phase 5 — Rules & Safety Decision Engine: Acceptance Record

**Date:** 2026-06-10
**Result:** ✅ PASS — all 15 synthetic referrals produce a schema-valid, fully reason-coded decision; `match_result`, `bot_decision` and `final_status` match the Phase 3 oracles exactly (15/15). Every decision carries ≥1 reason code; every risky case routes to a human.

## What was built
`services/rules-engine/` — the deterministic clinical-safety decision layer that **owns safety** (the LLM never reaches here):
- **`src/patient_repository.py`** — patient lookup behind one interface, two backends: `LocalPatientRepository` (the committed `synthetic_patients.json`; honours `seed_to_openmrs`, carries `existing_referral_status`) for the offline gate, and `OpenmrsPatientRepository` (live OpenMRS REST, stdlib `urllib`) for the Phase 8 production path.
- **`src/matcher.py`** — identifier-first patient matching with a demographic fallback → `EXACT_MATCH` / `DOB_MISMATCH` / `PARTIAL_MATCH` / `MULTIPLE_CANDIDATES` / `NO_MATCH` / `NOT_APPLICABLE`, plus same-patient-same-speciality duplicate detection.
- **`src/rules.py`** — deterministic safety rules. Each condition raises a safety flag + a machine-readable reason code; **any** flag blocks auto-create.
- **`src/decision_engine.py`** — orchestrator (match → rules → assemble → validate).
- **`src/validate.py`** + **`schema/decision.schema.json`** — Draft-07 validation (with a stdlib fallback). The schema **requires** a non-empty `reason_codes` array.
- **`run_decisions.py`** (CLI), **`validate_against_oracles.py`** (acceptance harness), **`app.py`** (stdlib HTTP service at `:8090`, no Flask).

## Scope boundary (what Phase 5 does NOT do)
The engine **decides** the outcome; it does not perform it. The actual OpenMRS write + re-read verify (for `AUTO_CREATE`) and the review-store write (for `HUMAN_REVIEW`) are Phase 6/8/9. `final_status` is therefore the **intended** terminal status.

## The two safety invariants (the headline gate)
1. **Every decision carries at least one reason code** — enforced by the schema (`reason_codes` `minItems: 1`) and re-checked by the harness.
2. **Any safety flag blocks auto-create** — `AUTO_CREATE_REFERRAL_RECORD` is emitted only when zero safety flags are raised. Match-risk, duplicate, urgent/2WW, safeguarding, child, incomplete, and low-confidence cases always route to a human.

## How to reproduce
```bash
cd services/rules-engine
python run_decisions.py             # writes data/decisions/REF-NNN.decision.json
python validate_against_oracles.py  # re-extracts, decides, compares to oracles; exit 0 = all 15 pass
```
Fully reproducible offline: matching runs against the committed synthetic-patient seed file (no Docker/network).

## Gate philosophy (exact where it matters, coverage where the oracle is a headline)
The three **safety-critical categoricals** — `match_result`, `bot_decision`, `final_status` — are checked for **exact** equality against the oracles. `safety_flags` and `reason_codes` are checked for **coverage**: every *expected* flag/reason must be present, but the engine derives codes mechanically and is deliberately more thorough than the oracle's hand-written "headline" set, so any **extra** flag/reason is reported as `INFO`, not a failure (the same convention the Phase 4 harness used for REF-013).

This does **not** weaken the gate: an extra flag on a clean (`AUTO_CREATE`) case would flip its decision to review and fail the exact `bot_decision` check. The only INFO divergences are the engine being *more* cautious:

| Ref | Engine extra (INFO) | Why it is correct |
|---|---|---|
| REF-009 | reason `URGENT_RED_FLAG` | Florence Cole's referral is marked *Urgent*; the engine records urgency alongside safeguarding+child rather than dropping it. Still routes to human. |
| REF-012 | reason `MATCH_EXACT` | The identity *is* an exact match; the engine records the match reason as well as the incomplete-fields reason. Still routes to human. |
| REF-013 | flag `INCOMPLETE_REFERRAL` + reasons `INCOMPLETE_MANDATORY_FIELDS`, `MATCH_EXACT` | On the degraded scan the regex path genuinely could not read speciality/priority/reason, so the referral *is* incomplete from the bot's view — which only reinforces routing to a human. |

## Per-referral gate result
```
REF      MATCH                DECISION                     REASON CODES
REF-001  EXACT_MATCH          AUTO_CREATE_REFERRAL_RECORD  MATCH_EXACT
REF-002  EXACT_MATCH          AUTO_CREATE_REFERRAL_RECORD  MATCH_EXACT
REF-003  EXACT_MATCH          AUTO_CREATE_REFERRAL_RECORD  MATCH_EXACT
REF-004  DOB_MISMATCH         HUMAN_REVIEW_REQUIRED        MATCH_DOB_MISMATCH
REF-005  PARTIAL_MATCH        HUMAN_REVIEW_REQUIRED        MATCH_PARTIAL
REF-006  MULTIPLE_CANDIDATES  HUMAN_REVIEW_REQUIRED        MATCH_MULTIPLE_CANDIDATES
REF-007  EXACT_MATCH          HUMAN_REVIEW_REQUIRED        MATCH_EXACT, DUPLICATE_REFERRAL
REF-008  EXACT_MATCH          HUMAN_REVIEW_REQUIRED        MATCH_EXACT, URGENT_RED_FLAG          (+ flag SUSPECTED_CANCER)
REF-009  EXACT_MATCH          HUMAN_REVIEW_REQUIRED        MATCH_EXACT, URGENT_RED_FLAG, SAFEGUARDING, CHILD_PATIENT
REF-010  NO_MATCH             HUMAN_REVIEW_REQUIRED        MATCH_NONE
REF-011  NO_MATCH             HUMAN_REVIEW_REQUIRED        MATCH_NONE
REF-012  EXACT_MATCH          HUMAN_REVIEW_REQUIRED        MATCH_EXACT, INCOMPLETE_MANDATORY_FIELDS
REF-013  EXACT_MATCH          HUMAN_REVIEW_REQUIRED        MATCH_EXACT, INCOMPLETE_MANDATORY_FIELDS, LOW_EXTRACTION_CONFIDENCE
REF-014  NOT_APPLICABLE       BUSINESS_EXCEPTION           NOT_A_REFERRAL
REF-015  NOT_APPLICABLE       SYSTEM_EXCEPTION             FILE_UNREADABLE

GATE RESULT: 15/15 referrals pass the decision acceptance
```

## Coverage demonstrated
- **Bot decisions:** `AUTO_CREATE` ×3, `HUMAN_REVIEW` ×10, `BUSINESS_EXCEPTION` ×1, `SYSTEM_EXCEPTION` ×1.
- **Match results:** exact, DOB-mismatch, partial, multiple-candidate, no-match, not-applicable.
- **Safety routing reasons:** patient-match risk, patient-not-found, duplicate, urgent/2WW, safeguarding, child, incomplete, low confidence, not-a-referral, unreadable.
- **A perfect patient match never bypasses a content gate:** REF-012 (exact match, incomplete) and REF-013 (exact match, low confidence) both route to a human.

## Duplicate-check dependency (REF-007)
The duplicate scenario needs Arthur Reed's pre-existing active Cardiology referral. The `local-seed` backend carries `existing_referral_status: "active:Cardiology"`, so the duplicate logic is proven **now**. The `openmrs` backend reports `"none"` until the `Referral` encounter type/concepts exist (Phase 6), at which point the live duplicate check (query encounters) activates. Documented in `data/expected-outcomes/README.md`.

## Artefacts produced
- `data/decisions/REF-001..015.decision.json` (15 files; gitignored runtime output, regenerate anytime).
- `services/rules-engine/` (source, schema, CLI, HTTP service, acceptance harness, README).

## Screenshots to capture (portfolio)
- `python validate_against_oracles.py` showing **GATE RESULT: 15/15**.
- A pretty-printed `REF-007` (duplicate) and `REF-009` (safeguarding child) decision JSON.
- `GET /health` + a `POST /decide` response from the running service.

## Next — Phase 6
OpenMRS workflow mapping: a concrete, executable update path — define the `Referral` encounter type + concepts, seed Arthur Reed's pre-existing active Cardiology referral (activating the live duplicate check), and specify the REST create + re-read-verify the bot performs for an `AUTO_CREATE` decision.
