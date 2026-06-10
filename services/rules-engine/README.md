# Rules & safety decision engine (Phase 5)

> **Synthetic data only.** Consumes a Phase 4 extraction result, matches the
> patient against OpenMRS (or the synthetic-patient seed file, offline), applies
> deterministic clinical-safety rules, and produces a fully reason-coded routing
> decision. This is the layer that **owns safety** — the LLM never reaches here.

A decided referral comes out of this engine as one of four outcomes, and **every
decision carries at least one reason code**. The core safety invariant: **any
safety flag blocks auto-create** — only a clean, complete, exactly-matched,
legible, non-urgent, non-duplicate referral is ever auto-created; everything
risky, uncertain, urgent, incomplete, duplicate, or match-ambiguous is routed to
a human.

## What it does

For each extraction (`data/extracted-json/REF-NNN.extracted.json`) it produces
`data/decisions/REF-NNN.decision.json`:

1. **Match the patient** (architecture steps 6–7). Identifier-first, with a
   demographic fallback:

   | Situation | `match_result` |
   |---|---|
   | NHS number resolves, surname + DOB agree | `EXACT_MATCH` |
   | NHS number resolves, demographics conflict | `DOB_MISMATCH` |
   | No/unfound NHS number, name + DOB match one patient | `PARTIAL_MATCH` |
   | No/unfound NHS number, name + DOB match several | `MULTIPLE_CANDIDATES` |
   | Nothing matches | `NO_MATCH` |
   | Not a referral / unreadable file | `NOT_APPLICABLE` |

2. **Apply the safety rules** (architecture steps 8–9). Each condition raises a
   safety flag and a machine-readable reason code:

   | Condition | Safety flag | Reason code |
   |---|---|---|
   | DOB / partial / multiple match | `PATIENT_MATCH_RISK` | `MATCH_DOB_MISMATCH` / `MATCH_PARTIAL` / `MATCH_MULTIPLE_CANDIDATES` |
   | No patient found | `PATIENT_NOT_FOUND` | `MATCH_NONE` |
   | Same patient + speciality + active referral | `DUPLICATE_REFERRAL_RISK` | `DUPLICATE_REFERRAL` |
   | Mandatory clinical fields missing | `INCOMPLETE_REFERRAL` | `INCOMPLETE_MANDATORY_FIELDS` |
   | Low extraction confidence (degraded scan) | `LOW_CONFIDENCE_EXTRACTION` | `LOW_EXTRACTION_CONFIDENCE` |
   | Urgent / red-flag content | `URGENT_RED_FLAG` | `URGENT_RED_FLAG` |
   | Suspected cancer / 2WW | `SUSPECTED_CANCER` | *(flag only — routed via the urgent red flag)* |
   | Safeguarding content | `SAFEGUARDING` | `SAFEGUARDING` |
   | Paediatric (child) patient | `CHILD_PATIENT` | `CHILD_PATIENT` |

3. **Decide** (architecture step 10). One decision per referral:

   | Bot decision | When | Final status |
   |---|---|---|
   | `AUTO_CREATE_REFERRAL_RECORD` | Exact match, complete, legible, non-urgent, no duplicate — **no safety flag** | `REFERRAL_CREATED_IN_OPENMRS` |
   | `HUMAN_REVIEW_REQUIRED` | **Any** safety flag raised | `ROUTED_TO_HUMAN_REVIEW` |
   | `BUSINESS_EXCEPTION` | Readable but not a referral | `BUSINESS_EXCEPTION_FAILED` |
   | `SYSTEM_EXCEPTION` | File could not be read/parsed | `SYSTEM_EXCEPTION_ESCALATED` |

4. **Validate** the result against
   [`schema/decision.schema.json`](schema/decision.schema.json) before it is
   returned/written.

> The engine **decides** the outcome; it does not perform it. The actual OpenMRS
> write + verify (for auto-create) and the review-store write (for human review)
> are Phase 6/8/9.

### Why a missing NHS number is *not* an "incomplete" referral

A missing identifier is a patient-**matching** concern (it drives
`PARTIAL_MATCH` / `MULTIPLE_CANDIDATES`), not a referral-**content** gap, so it is
excluded from the completeness check. That is why REF-005/006 are match-risk
cases, not "incomplete" cases — and why REF-012 (perfect identity, no
speciality/priority/reason) is the one that trips `INCOMPLETE_REFERRAL`.

## Patient match backends (one interface, two sources)

* **`local-seed` (default)** — the committed `synthetic_patients.json`. A patient
  is "present" iff `seed_to_openmrs` is true, so the reserved no-match fixtures
  correctly return `NO_MATCH`, and `existing_referral_status` is carried so the
  duplicate scenario (REF-007) is exercised **offline and deterministically**.
  No Docker, no network — the same guardrail philosophy as the Phase 4 regex path.
* **`openmrs`** — live OpenMRS REST (stdlib `urllib`, same auth/host as the Phase 2
  seeder). The production path the UiPath performer uses in Phase 8.

> **Duplicate-check dependency:** the `openmrs` backend reports
> `existing_referral_status = "none"` until the `Referral` encounter type/concepts
> exist (Phase 6). Until then the live duplicate check is inert; the `local-seed`
> backend carries the status so the gate still proves the duplicate logic. This is
> the dependency noted in `data/expected-outcomes/README.md`.

## Run it

```bash
cd services/rules-engine

# Decide all referrals -> data/decisions/  (needs Phase 4 extracted-json present)
python run_decisions.py
python run_decisions.py REF-007 REF-008      # subset
python run_decisions.py --source openmrs     # match against live OpenMRS REST

# Phase 5 ACCEPTANCE: re-extract + decide + compare to the Phase 3 oracles
python validate_against_oracles.py           # exit 0 = all 15 pass the gate

# Optional: run as an HTTP service the UiPath performer can call (stdlib only)
python app.py                                 # http://0.0.0.0:8090
#   GET  /health
#   POST /decide  {"extraction": {...}, "source": "local|openmrs"}
```

## Layout

```
schema/decision.schema.json     Output JSON Schema (Draft-07)
src/patient_repository.py        Patient lookup: LocalPatientRepository + OpenmrsPatientRepository
src/matcher.py                   Extraction -> match_result (+ duplicate detection)
src/rules.py                     Deterministic safety rules: flags, reason codes, decision
src/decision_engine.py           Orchestrator (match -> rules -> assemble -> validate)
src/validate.py                  Schema validation (jsonschema, with stdlib fallback)
run_decisions.py                 CLI: extracted-json/ -> decisions/
validate_against_oracles.py      Phase 5 acceptance harness vs Phase 3 oracles
app.py                           Minimal stdlib HTTP wrapper (no Flask dependency)
```

## Acceptance & the gate philosophy

`validate_against_oracles.py` re-runs the Phase 4 extraction, decides each
referral against the seed file, and compares to the Phase 3 oracles. The three
**safety-critical categoricals** — `match_result`, `bot_decision`,
`final_status` — are checked for **exact** equality. `safety_flags` and
`reason_codes` are checked for **coverage**: the engine derives codes
mechanically and is deliberately more thorough than the oracle's hand-written
"headline" set, so any **extra** flag/reason is reported as `INFO`, not a
failure (the same convention the Phase 4 harness used for REF-013).

This never weakens the gate: an extra flag on a clean case would flip its
decision away from `AUTO_CREATE` and fail the exact decision check. Result:
**15/15 pass.** Evidence:
[`docs/testing/phase5-acceptance.md`](../../docs/testing/phase5-acceptance.md).
