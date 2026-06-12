# Phase 7 — REFramework Design Spec: Acceptance Record

**Date:** 2026-06-12
**Result:** ✅ PASS — the UiPath build is fully specified from existing, tested
services. A developer can build Phase 8 from the spec alone; every input, output,
service call, branch and exception path is named, and **Business vs System
exceptions are explicitly separated**. Gate: **12/12** design-review checks.

## What was produced
A design phase — no code runs; the deliverable is the *buildable contract* for the
Phase 8 UiPath build.
- **[`uipath/design/reframework-design-spec.md`](../../uipath/design/reframework-design-spec.md)** — the full design: project identity, Dispatcher, queue-item schema, Config workbook, Assets/Credentials, the REFramework state machine, `Process.xaml` per-transaction flow, the OpenMRS write/verify sub-sequence, the **BE vs SE policy**, idempotency, and the 15-scenario traceability matrix.
- **[`uipath/design/Config.xlsx`](../../uipath/design/Config.xlsx)** — the REFramework Config workbook (Settings / Constants / Assets) the Performer ships with.
- **[`uipath/README.md`](../../uipath/README.md)** — pointer for the `uipath/` solution area.

## Acceptance checks (design review — all PASS, 12/12)
| # | Check (is the build unambiguous?) | Evidence in spec |
|---|---|---|
| 1 | Dispatcher behaviour defined | §3 — enumerate `REF-*`, Add Queue Item, unique Reference |
| 2 | Queue-item schema defined (in + output) | §4 — SpecificContent + output/analytics keys |
| 3 | Idempotent enqueue | §4/§9 — Reference = `ReferralId`, unique-reference constraint |
| 4 | Config workbook fully specified | §5.1 — Settings/Constants/Assets named with values |
| 5 | Assets & credentials specified, secrets handled | §5.2 — `NHS_OpenMRS_Credential`; LLM key stays in the service, never in UiPath |
| 6 | Performer state machine mapped to REFramework | §6 — per-state customisation table + `Process.xaml` args |
| 7 | Per-transaction flow calls the real services | §7 — POST `/extract`, POST `/decide`, parse + persist artefacts |
| 8 | OpenMRS write/verify sequence specified | §7.1 — find→idempotency→create→re-read verify, mirrors Phase 6 |
| 9 | **Business vs System exceptions separated** | §8 — two-layer table; HUMAN_REVIEW = success, not exception |
| 10 | Retry / escalation mechanics defined | §8 — BusinessRuleException (no retry) vs Exception (retry→screenshot→escalate) |
| 11 | Idempotency / safe re-run end-to-end | §9 — queue, OpenMRS source-id no-op, append-only audit |
| 12 | All 15 Phase 3 scenarios have a defined path | §10 — 3 AUTO_CREATE, 10 HUMAN_REVIEW, 1 BE, 1 SE |

## The BE/SE separation (the headline gate)
Two independent layers, both explicit:
- **Layer 1 — decided by the engine.** The Phase 5 `bot_decision` maps 1:1 to a
  REFramework status: AUTO_CREATE / HUMAN_REVIEW → **Successful** (queue item);
  BUSINESS_EXCEPTION → **Failed (Business)**, no retry; SYSTEM_EXCEPTION →
  **Failed (Application)**, retried then escalated.
- **Layer 2 — operational.** Service `5xx`/timeout, OpenMRS unreachable/verify
  mismatch, malformed responses → **System** (retry); non-synthetic input →
  **Business** (no retry).

Reviewer-critical point captured in the design: **HUMAN_REVIEW is a success
outcome, not an exception.** Routing a risky/ambiguous/urgent/duplicate/incomplete
case to a human is the *designed safe behaviour*; only genuine bad input
(not-a-referral) is a Business Exception.

## Traceability — the Phase 8 test matrix
| Scenarios | Decision | TX status |
|---|---|---|
| Bennett, Davies, Clarke | AUTO_CREATE | 3 × Successful → `processed/` |
| Shaw, Hamilton, Walsh, Reed, Knight, Cole, Fernandes, Osei, Owen, Roberts | HUMAN_REVIEW | 10 × Successful → `review/` |
| REF-014 (not a referral) | BUSINESS_EXCEPTION | Failed (Business) → `failed/` |
| REF-015 (corrupt PDF) | SYSTEM_EXCEPTION | Failed (Application) → `failed/` |

Expected Phase 8 run: **3 processed, 10 review, 1 BE-failed, 1 SE-failed.**

## Scope boundary (what Phase 7 does NOT do)
Phase 7 produces the design only. No `.xaml` is built and nothing is run — that is
Phase 8 (UiPath build). The human-review store and audit DB are *referenced* with
reserved paths; their implementations are Phase 9. The LLM extraction path remains
inside the Phase 4 service, unreachable from the bot.

## Artefacts produced
- `uipath/design/reframework-design-spec.md`
- `uipath/design/Config.xlsx`
- `uipath/README.md`
- `docs/testing/phase7-acceptance.md` (this file)

## Screenshots to capture (portfolio)
- The BE/SE policy table (§8) — the clearest single artefact of REFramework
  exception thinking for an interviewer.
- The state-machine / `Process.xaml` flow (§6–§7).
- `Config.xlsx` Settings sheet.

## Next — Phase 8
UiPath build: implement the Dispatcher and REFramework Performer from this spec,
set up the `NHS_Referrals` queue + `NHS_OpenMRS_Credential` asset, and run the
§10 matrix — clean → OpenMRS, risky → review, duplicate detected, BE/SE distinct.
