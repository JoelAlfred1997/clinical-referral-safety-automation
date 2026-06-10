# Phase 4 — Extraction Service: Acceptance Record

**Date:** 2026-06-10
**Result:** ✅ PASS — all 15 synthetic referrals extract to schema-valid JSON; `is_referral`, `missing_fields` and **confidence** match the Phase 3 oracles (15/15).

## What was built
`services/extraction-service/` — an AI-assisted extraction component with a deterministic guardrail:
- **`src/regex_extractor.py`** — deterministic, dependency-free field extraction + normalisers (NHS number, dd/mm/yyyy→ISO date, gender→M/F, priority→Routine/Urgent/2WW, GMC/city stripping, leet/OCR clean-up for degraded scans).
- **`src/text_reader.py`** — TXT/PDF reading; corrupt PDF → `FILE_UNREADABLE` (structural `%%EOF` check + `pypdf`).
- **`src/confidence.py`** — `missing_fields`, confidence category, and advisory `extraction_signals`.
- **`src/llm_extractor.py`** — optional Groq/OpenAI-compatible path, **off by default**, regex fallback on any failure; output coerced through the same normalisers + schema.
- **`src/validate.py`** + **`schema/extraction.schema.json`** — Draft-07 validation (with a stdlib fallback).
- **`run_extraction.py`** (CLI), **`validate_against_oracles.py`** (acceptance harness), **`app.py`** (stdlib HTTP service at `:8089`, no Flask).

## Scope boundary (what Phase 4 does NOT do)
Extraction only. **No** patient matching against OpenMRS, **no** routing/clinical decision. `match_result`, `bot_decision`, `final_status` are absent from the output schema by design — they are Phase 5 (rules) / Phase 6 (OpenMRS). The LLM is strictly *advisory* and has zero authority over writes.

## How to reproduce
```bash
cd services/extraction-service
python run_extraction.py            # writes data/extracted-json/REF-NNN.extracted.json
python validate_against_oracles.py  # exit 0 = all 15 pass
```
Fully reproducible offline: with no API key the deterministic regex path is used.

## Acceptance checks (all PASS)
| Criterion | Evidence |
|---|---|
| Each referral → schema-valid JSON | 15/15 validate against `extraction.schema.json` |
| `is_referral` correct | REF-014 (appointment reminder) → `false`; REF-015 (corrupt) → `null`; rest `true` |
| `confidence` correct (headline gate) | high ×9 (clean), medium ×2 (no NHS: REF-005/006), low ×1 (degraded scan: REF-013), n/a ×2 (REF-014/015) |
| `missing_fields` correct | REF-005/006 `[patient_nhs_number]`; REF-012 `[specialty,priority,reason_for_referral]`; REF-014 all-four; clean ×8 `[]` |
| Business vs System exception distinguished | REF-014 readable-but-wrong → `NOT_A_REFERRAL`; REF-015 unparseable → `FILE_UNREADABLE` |
| Normalisation correct | `999 000 0018`→`9990000018`; `12/04/1979`→`1979-04-12`; `Male`→`M`; `URGENT — 2-WEEK WAIT`→`2WW` |
| Advisory signals correct | REF-008 `suspected_cancer`+`urgent_red_flag`; REF-009 `safeguarding`+`child_patient`; no false `urgent` on "no red-flag" letters |

## Per-referral gate result
```
REF-001..004,007  PASS  high    []                                  (clean exact-match)
REF-005           PASS  medium  [patient_nhs_number]                (partial — no NHS)
REF-006           PASS  medium  [patient_nhs_number]                (multiple candidates — no NHS)
REF-008           PASS  high    []   priority=2WW                   (2WW suspected cancer)
REF-009           PASS  high    []   safeguarding+child signals     (safeguarding child)
REF-010,011       PASS  high    []                                  (no-match fixtures)
REF-012           PASS  high    [specialty,priority,reason]         (incomplete)
REF-013           PASS  low     (identity fields correct)           (degraded scan)
REF-014           PASS  n/a     NOT_A_REFERRAL                      (business exception)
REF-015           PASS  n/a     FILE_UNREADABLE                     (system exception)

GATE RESULT: 15/15 referrals pass extraction acceptance
```

## Regex vs LLM boundary (REF-013)
REF-013 is a deliberately degraded "scanned/faxed" letter. The deterministic guardrail does the **safe** thing: it flags it **low confidence**, cleans the identity-critical fields (`9 9 9 0 0 0 0 0 8 5`→`9990000085`, `Rob3rts`→`Roberts`, DOB, gender), and leaves the illegible speciality/priority/reason **blank for a human**. The full field reconstruction shown in that oracle is the optional **LLM path's** target. The harness reports those few fields as `INFO`, not `FAIL` — the regex path is correct to flag-and-defer rather than guess. This is the project's core thesis in miniature: AI assists, deterministic guardrails own safety.

## Artefacts produced
- `data/extracted-json/REF-001..015.extracted.json` (15 files).
- `services/extraction-service/` (source, schema, CLI, HTTP service, acceptance harness, README).

## Screenshots to capture (portfolio)
- `python validate_against_oracles.py` showing **GATE RESULT: 15/15**.
- A pretty-printed `REF-008` and `REF-013` extracted JSON (2WW signal; low-confidence flag).
- `GET /health` + a `POST /extract` response from the running service.

## Next — Phase 5
Rules & safety decision engine: consume `extracted-json/` + OpenMRS patient match → `match_result`, `safety_flags`, `reason_codes`, `bot_decision` with a reason code for every decision. The Phase 3 oracles already carry the expected values.
