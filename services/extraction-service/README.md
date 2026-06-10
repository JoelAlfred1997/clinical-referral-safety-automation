# Extraction service (Phase 4)

> **Synthetic data only.** Turns a referral document into a schema-validated
> extraction JSON. It does **not** match patients and makes **no** clinical or
> routing decision — those are the deterministic rules engine (Phase 5) against
> OpenMRS (Phase 6).

This is the "AI-assisted extraction with deterministic guardrails" component of
the Clinical Referral Safety Automation. A document goes in; structured fields,
a completeness report, and a confidence rating come out.

## What it does

For each referral (`data/input-referrals/REF-NNN.*`) it produces
`data/extracted-json/REF-NNN.extracted.json`:

1. **Read** the file (TXT, or PDF via `pypdf`). A file that can't be parsed →
   `extraction_status: FILE_UNREADABLE` (a *System Exception* input for the bot).
2. **Classify** referral vs not-a-referral. A readable but wrong document (e.g.
   an appointment reminder) → `NOT_A_REFERRAL` (a *Business Exception* input).
3. **Extract** the 11 referral fields. Default path is the deterministic
   **regex** extractor; the optional **LLM** path runs only when `USE_LLM=true`
   and an API key is set, and any LLM failure falls back to regex. Both paths go
   through the **same** normalisers and the **same** schema validation.
4. **Score** completeness (`missing_fields`) and **confidence**
   (`high`/`medium`/`low`/`n/a`).
5. **Validate** against [`schema/extraction.schema.json`](schema/extraction.schema.json)
   before the result is returned/written.

### Confidence logic (deterministic, auditable)

Confidence is about *extraction quality*, not completeness:

| Confidence | When |
|---|---|
| `high`   | Legible, NHS number present. |
| `medium` | Legible but **no NHS number** — identity rests on demographics only. |
| `low`    | **Degraded scan/fax** (illegible / poor-quality markers detected). |
| `n/a`    | Not a referral, or unreadable file. |

A perfectly legible but *incomplete* referral is still `high` confidence — its
gaps show up in `missing_fields`, which is what routes it to a human (Phase 5).

### Advisory signals (non-authoritative)

`extraction_signals` (`urgent_red_flag`, `suspected_cancer`, `safeguarding`,
`child_patient`) are **hints** for the Phase 5 rules engine. The extractor flags
them; it never routes or decides on them. This keeps the AI strictly *advisory*.

## Run it

```bash
cd services/extraction-service

# Extract all referrals -> data/extracted-json/ (regex path, no deps/keys needed)
python run_extraction.py
python run_extraction.py REF-008 REF-013     # subset
python run_extraction.py --file ../../data/input-referrals/REF-001-bennett-cardiology.txt

# Phase 4 ACCEPTANCE: compare every output to the Phase 3 oracles
python validate_against_oracles.py           # exit 0 = all 15 pass the gate

# Optional: run as an HTTP service the UiPath performer can call (stdlib only)
python app.py                                 # http://0.0.0.0:8089
#   GET  /health
#   POST /extract  {"path": "<abs path>"}
#   POST /extract  {"source_file": "REF-001.txt", "text": "<raw text>"}
```

### Enabling the LLM path (optional)

Set in `.env` (see repo root `.env.example`): `USE_LLM=true`, `LLM_PROVIDER=groq`,
`GROQ_API_KEY=...`. With no key the service silently uses the regex guardrail, so
the acceptance run is fully reproducible offline.

## Layout

```
schema/extraction.schema.json   Output JSON Schema (Draft-07)
src/text_reader.py              TXT/PDF reading + FILE_UNREADABLE detection
src/regex_extractor.py          Deterministic field extraction + normalisers
src/llm_extractor.py            Optional Groq/OpenAI-compatible path (guarded)
src/confidence.py               missing_fields, confidence, advisory signals
src/validate.py                 Schema validation (jsonschema, with stdlib fallback)
src/extractor.py                Orchestrator (read → classify → extract → score → validate)
run_extraction.py               CLI: extract input-referrals/ → extracted-json/
validate_against_oracles.py     Phase 4 acceptance harness vs Phase 3 oracles
app.py                          Minimal stdlib HTTP wrapper (no Flask dependency)
```

## Acceptance & the regex/LLM boundary

`validate_against_oracles.py` checks the extraction-level outputs Phase 4 owns —
schema validity, status, `is_referral`, **confidence**, `missing_fields`, and the
deterministically-extractable structured fields. Result: **15/15 pass**.

REF-013 is a deliberately degraded "scanned/faxed" letter. The regex guardrail
correctly flags it **low confidence** and gets the identity-critical fields
(cleaned NHS number, DOB, name) right, while leaving the illegible
speciality/priority/reason blank for a human. The full reconstruction shown in
that oracle is the optional **LLM path's** target, so those few fields are
reported as `INFO`, not failures — the deterministic path does the safe thing
(flag and defer) rather than guess. Evidence:
[`docs/testing/phase4-acceptance.md`](../../docs/testing/phase4-acceptance.md).
