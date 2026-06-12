# REFramework Design Specification (Phase 7)

> **Portfolio simulation. Synthetic data only. OpenMRS is a mock EPR/EMR.**
> This document is the *buildable* design for the UiPath build (Phase 8). It turns
> the Phase 4 (extraction), Phase 5 (rules/decision) and Phase 6 (OpenMRS
> write/verify) services into a concrete UiPath **Dispatcher + REFramework
> Performer** design: queue-item schema, Config workbook, Assets/Credentials,
> the per-transaction state machine, and an explicit **Business- vs
> System-Exception** policy. A UiPath developer can build Phase 8 from this file
> alone — every input, output, service call, branch and exception path is named.

**Phase 7 acceptance gate:** *Buildable from the spec; BE/SE separated.*
Evidence and the design-review checklist that closes the gate:
[`docs/testing/phase7-acceptance.md`](../../docs/testing/phase7-acceptance.md).

---

## 1. Project identity & layout

| Item | Value |
|---|---|
| Solution name | `NHS.ReferralSafety` |
| Dispatcher process | `NHS.ReferralSafety.Dispatcher` |
| Performer process | `NHS.ReferralSafety.Performer` (REFramework) |
| Execution mode | Unattended-style; runnable attended for demo/screenshots |
| Orchestrator queue | `NHS_Referrals` |
| Project folder | `uipath/` (Studio projects live here; this spec is the contract) |

```
uipath/
  design/
    reframework-design-spec.md   <- this file (the build contract)
    Config.xlsx                  <- the Config workbook Phase 8 ships in the Performer
  NHS.ReferralSafety.Dispatcher/ <- (Phase 8) Studio project
  NHS.ReferralSafety.Performer/  <- (Phase 8) Studio project (REFramework template)
```

The Performer is the **standard REFramework template** (Main.xaml state machine:
`Init → Get Transaction Data → Process Transaction → End Process`). Only the
files listed in §6 are customised; everything else stays as the template ships,
which keeps the build reviewable against a known baseline.

---

## 2. Where Phase 7 sits in the pipeline

Phase 7 does not run anything new — it *specifies* how the bot orchestrates the
already-built and already-tested services:

```
Phase 4 extraction service (HTTP :8089)  ─┐
Phase 5 decision service    (HTTP :8090)  ─┼─►  Phase 8 Performer (this design)
Phase 6 OpenMRS write/verify (REST)       ─┘
```

The architecture end-to-end flow is in
[`docs/technical/architecture.md`](../../docs/technical/architecture.md) §2; the
OpenMRS write/verify calls are in
[`docs/technical/openmrs-referral-workflow.md`](../../docs/technical/openmrs-referral-workflow.md).
This spec binds those into a transaction.

---

## 3. Dispatcher design (`NHS.ReferralSafety.Dispatcher`)

**Purpose:** enumerate synthetic referral files and push one queue item per file.
Kept deliberately thin — no business logic, no extraction. Idempotent by design.

**Steps**

1. Read `Config.xlsx` (or assets) for `InputFolder` and `OrchestratorQueueName`.
2. `For Each` file in `InputFolder` matching `REF-*.txt` and `REF-*.pdf`
   (the Phase 3 corpus: `REF-001..015`).
3. Derive `ReferralId` from the filename stem (`REF-015-corrupt.pdf → REF-015`).
4. `Add Queue Item` with **Reference = `ReferralId`** and the SpecificContent in §4.
5. Skip files already enqueued: rely on the queue's **Unique Reference**
   constraint (`Add Queue Item` set to enforce unique reference) so re-running the
   Dispatcher never double-enqueues the same referral.

> The Dispatcher does **not** move or delete input files — the Performer owns file
> movement so a failed transaction can be re-driven from the original input.

---

## 4. Queue item schema (`NHS_Referrals`)

`Add Queue Item` → **SpecificContent** (what the Dispatcher writes):

| Key | Type | Example | Notes |
|---|---|---|---|
| `ReferralId` | String | `REF-001` | Also the queue item **Reference** (idempotency / dedupe key). |
| `SourceFile` | String | `REF-001.txt` | File name only. |
| `SourcePath` | String | `data/input-referrals/REF-001.txt` | Path the extraction service can read (same host/container). |
| `FileType` | String | `txt` \| `pdf` | From the extension. |
| `Synthetic` | Boolean | `True` | Hard constraint guard; Performer asserts this is `True`. |
| `EnqueuedAtUtc` | DateTime | `2026-06-12T09:00:00Z` | Audit. |

**Reference:** `ReferralId`. **Priority:** `Normal` (no clinical prioritisation —
the bot routes, clinicians decide; see scope §4).

**Output / Analytics data** the Performer sets on the item at completion (for
reporting in Phase 10 and immediate queue-level evidence):

| Key | Example |
|---|---|
| `BotDecision` | `AUTO_CREATE_REFERRAL_RECORD` |
| `FinalStatus` | `REFERRAL_CREATED_IN_OPENMRS` |
| `MatchResult` | `EXACT_MATCH` |
| `ReasonCodes` | `MATCH_EXACT` |
| `EncounterUuid` | `<uuid>` (AUTO_CREATE only) |
| `ReviewId` | `<id>` (HUMAN_REVIEW only) |

These values are the public contract of the Phase 5 decision (see
`services/rules-engine/schema/decision.schema.json`); the Performer copies them
through, it does not invent them.

---

## 5. Config workbook & Assets

### 5.1 `Config.xlsx`

Standard REFramework three-sheet workbook. Shipped at
[`uipath/design/Config.xlsx`](Config.xlsx); copy into the Performer's `Data/`
folder in Phase 8. Sheet contents (also see the generated workbook for the live
values):

**Settings**

| Name | Value | Purpose |
|---|---|---|
| `OrchestratorQueueName` | `NHS_Referrals` | Queue the Performer drains. |
| `logF_BusinessProcessName` | `NHS.ReferralSafety` | Log field. |
| `ExtractionServiceUrl` | `http://localhost:8089` | Phase 4 service base. |
| `DecisionServiceUrl` | `http://localhost:8090` | Phase 5 service base. |
| `PatientMatchSource` | `openmrs` | `openmrs` (live) or `local-seed` (offline). Passed as `source` to `/decide`. |
| `OpenMrsRestUrl` | `http://localhost/openmrs/ws/rest/v1` | OpenMRS REST root for Phase 6 write/verify. |
| `ReferralMetadataPath` | `services/openmrs-workflow/config/referral-metadata.json` | Resolved encounter-type/concept/location UUIDs. |
| `InputFolder` | `data/input-referrals` | Dispatcher source. |
| `ProcessedFolder` | `data/processed` | AUTO_CREATE success destination. |
| `ReviewFolder` | `data/review` | HUMAN_REVIEW destination. |
| `FailedFolder` | `data/failed` | BE / exhausted-SE destination. |
| `ExtractedJsonFolder` | `data/extracted-json` | Per-referral extraction artefact. |
| `DecisionsFolder` | `data/decisions` | Per-referral decision artefact. |
| `AuditDbPath` | `data/audit/audit.sqlite` | Append-only audit (Phase 9 store; path reserved now). |
| `ReviewStorePath` | `data/review/review.sqlite` | Human-review store (Phase 9). |
| `ServiceHttpTimeoutSec` | `60` | HTTP Request timeout for service calls. |
| `MaxRetryNumber` | `2` | REFramework system-exception retries (overridden by queue `Max # of retries` if set). |

**Constants** (REFramework defaults, listed for completeness)

| Name | Value |
|---|---|
| `RetryNumberGetTransactionItem` | `3` |
| `RetryNumberSetTransactionStatus` | `3` |
| `MaxConsecutiveSystemExceptions` | `5` |

**Assets** (name in workbook → Orchestrator asset name)

| Name | Orchestrator asset | Type |
|---|---|---|
| `OpenMrsCredential` | `NHS_OpenMRS_Credential` | **Credential** (synthetic local: `admin` / `Admin123`) |

### 5.2 Credentials & secrets

- **OpenMRS** Basic-auth credential is the only secret the **bot** holds, stored as
  an Orchestrator **Credential asset** (`NHS_OpenMRS_Credential`) and read with
  `Get Credential`. It authenticates the Phase 6 REST write/verify calls.
- **LLM API key is NOT a UiPath asset.** The LLM only ever runs *inside the Phase 4
  extraction service*, behind its deterministic regex fallback (scope §3, Phase 0
  decision: AI has zero authority over writes). The key lives in that service's
  `.env` (`GROQ_API_KEY`, see `.env.example`), never in Orchestrator and never in
  the workflow. The Performer cannot reach an LLM even in principle.
- No secrets are committed; `referral-metadata.json` is generated and gitignored
  (instance-specific UUIDs), read at runtime from `ReferralMetadataPath`.

---

## 6. Performer state machine (REFramework)

Standard REFramework Main.xaml. Customisation per state:

| State | Customisation |
|---|---|
| **InitAllSettings** | Loads `Config.xlsx`, reads Assets, `Get Credential` for OpenMRS. |
| **InitAllApplications** | Health-check the two services (`GET /health` on Extraction + Decision) and OpenMRS (`GET /session` authenticated). A failed health check here is a **System Exception** → the run does not start processing against a dead dependency. |
| **GetTransactionData** | Standard `Get Transaction Item` from `NHS_Referrals`. Stop when `Nothing`. |
| **Process** | `Process.xaml` — the in-transaction logic in §7. |
| **SetTransactionStatus** | Standard REFramework BE/SE handling (§8) + per-outcome file move and audit row. |
| **EndProcess** | Standard. No app to close. |

`in_TransactionItem` is the queue item; `Process.xaml` arguments:

| Arg | Dir | Type | Notes |
|---|---|---|---|
| `in_TransactionItem` | In | QueueItem | The referral. |
| `in_Config` | In | Dictionary | The Config workbook + assets. |
| `out_Decision` | Out | JObject | Parsed decision JSON (drives SetTransactionStatus + output data). |
| `out_FinalStatus` | Out | String | One of the four `final_status` values. |

---

## 7. `Process.xaml` — the per-transaction flow

One transaction = one referral. Steps, with the exception class each failure maps
to (see §8 for BE/SE rules):

1. **Guard** — assert `SpecificContent("Synthetic") = True`. If not → **Business
   Exception** (`NON_SYNTHETIC_INPUT`); this project never processes non-synthetic
   data.

2. **Extract** — `HTTP Request` `POST {ExtractionServiceUrl}/extract`
   body `{"path": SourcePath}`.
   - HTTP 200 → parse body as the Phase 4 extraction JSON; **save** it to
     `{ExtractedJsonFolder}/{ReferralId}.extracted.json` (audit artefact).
   - HTTP 5xx / timeout / connection refused → **System Exception** (transient
     infra; retry).
   - The extraction *content* (NOT_A_REFERRAL, FILE_UNREADABLE) is **not** an
     exception here — it is data the decision service classifies in step 3.

3. **Decide** — `HTTP Request` `POST {DecisionServiceUrl}/decide`
   body `{"extraction": <step-2 JSON>, "source": PatientMatchSource}`.
   - HTTP 200 → parse the Phase 5 decision JSON; **save** to
     `{DecisionsFolder}/{ReferralId}.decision.json`. This object holds
     `bot_decision`, `final_status`, `match_result`, `matched_patient`,
     `safety_flags`, `reason_codes`.
   - HTTP error / timeout → **System Exception** (retry).

4. **Branch on `bot_decision`** (the engine has already separated the four
   outcomes — the Performer executes them, it does not re-decide):

   - **`AUTO_CREATE_REFERRAL_RECORD`** → §7.1 OpenMRS write/verify.
     On success `final_status = REFERRAL_CREATED_IN_OPENMRS`.
   - **`HUMAN_REVIEW_REQUIRED`** → insert a row into the review store
     (`ReviewStorePath`; full implementation Phase 9) with `referral_id`,
     `reason_codes`, `match_result`, decision JSON. `final_status =
     ROUTED_TO_HUMAN_REVIEW`. **This is a SUCCESS outcome** (queue item
     *Successful*) — routing to a human is the correct, safe result, not a failure.
   - **`BUSINESS_EXCEPTION`** (e.g. REF-014 not-a-referral) → `Throw`
     **BusinessRuleException** carrying `reason_codes`. `final_status =
     BUSINESS_EXCEPTION_FAILED`.
   - **`SYSTEM_EXCEPTION`** (e.g. REF-015 corrupt PDF, `FILE_UNREADABLE`) →
     `Throw` a system `Exception`. `final_status = SYSTEM_EXCEPTION_ESCALATED`.

5. **Audit** — every outcome (including BE/SE) writes one append-only audit row in
   SetTransactionStatus (§8): `referral_id, bot_decision, final_status,
   match_result, reason_codes, encounter_uuid|review_id, before/after, robot,
   timestamp_utc`.

### 7.1 OpenMRS write/verify (AUTO_CREATE only)

Direct REST automation from UiPath (`HTTP Request` activities, Basic auth from
`OpenMrsCredential`) — this is the headline "REST automation against a real EMR"
capability and mirrors the verified Phase 6 path exactly
([`openmrs-referral-workflow.md`](../../docs/technical/openmrs-referral-workflow.md) §3):

1. **Find patient** — `GET /patient?q={matched_patient.nhs_number}&v=full` → patient `uuid`.
2. **Idempotency check** — query the patient's `Referral` encounters and look for a
   `Referral - Source Document ID` obs equal to `ReferralId`. If found → **no-op**
   (`action = exists`); still verify + audit. Re-runs create **no** duplicate record.
3. **Create** — `POST /encounter` with `patient`, `encounterType`, `location` (from
   `referral-metadata.json`), `encounterDatetime` = server-relative now, and one
   obs per field (speciality/urgency/reason/referrer_name/referrer_org/status=
   `active`/source_id=`ReferralId`, plus `suspected_cancer` when the flag is set).
4. **Verify by re-read** — `GET /encounter/{uuid}?v=custom:(...obs...)`; assert every
   written field round-trips. Only then is the referral "created".
5. Any OpenMRS failure (unreachable, 401, 5xx, verify mismatch) → **System
   Exception** (retry); a clean verify → move file to `ProcessedFolder`.

> **Note for Phase 8:** the live duplicate *clinical* check (different referral,
> same patient, same active speciality — REF-007 Arthur Reed) is already computed
> by the decision service when `PatientMatchSource = openmrs` (it reads live
> `existing_referral_status` and emits `DUPLICATE_REFERRAL_RISK` →
> `HUMAN_REVIEW_REQUIRED`). The idempotency check in step 2 is the *separate*
> "same source document" guard. Keep the two distinct.

---

## 8. Business vs System Exception policy (the acceptance gate)

Two independent layers produce the BE/SE split. Both are explicit so the build is
unambiguous.

### Layer 1 — decided by the engine (`bot_decision`)

The Phase 5 engine already classifies the *content* outcome. The Performer maps it
1:1 to a REFramework transaction status:

| `bot_decision` | REFramework status | Retried? | File → | `final_status` |
|---|---|---|---|---|
| `AUTO_CREATE_REFERRAL_RECORD` | **Successful** | n/a | `processed/` | `REFERRAL_CREATED_IN_OPENMRS` |
| `HUMAN_REVIEW_REQUIRED` | **Successful** | n/a | `review/` | `ROUTED_TO_HUMAN_REVIEW` |
| `BUSINESS_EXCEPTION` | **Failed (Business)** | **No** | `failed/` | `BUSINESS_EXCEPTION_FAILED` |
| `SYSTEM_EXCEPTION` | **Failed (Application)** | **Yes** | `failed/` after retries | `SYSTEM_EXCEPTION_ESCALATED` |

Key distinction for reviewers: **HUMAN_REVIEW is a success, not an exception.**
Routing a risky/ambiguous/urgent/duplicate case to a human is the *designed safe
outcome*. Only genuine bad input (not-a-referral) is a Business Exception.

### Layer 2 — operational failures during processing

Anything that throws while the transaction runs, regardless of `bot_decision`:

| Failure | Class | Why |
|---|---|---|
| Non-synthetic input guard fails | **Business** | Deterministic bad input; retry can't fix it. |
| Extraction/Decision service `5xx`/timeout/refused | **System** | Transient infra; retry. |
| OpenMRS unreachable / 401 / 5xx / verify mismatch | **System** | Transient infra; retry. |
| Corrupt/unreadable file (`FILE_UNREADABLE`) | **System** | Project convention (Phase 3 oracle REF-015); escalate for manual handling. |
| Malformed service response (schema/parse) | **System** | Treated as transient; surfaces in logs/screenshot. |

**Mechanics (standard REFramework):**
- **BusinessRuleException** → `SetTransactionStatus` marks the queue item *Failed*
  with reason **Business**, **no retry**, moves to the next transaction.
- Any other **Exception** → marked *Failed* with reason **Application**, retried up
  to `MaxRetryNumber` (or the queue's `Max # of retries`); on the final attempt
  **Take Screenshot** to `data/failed/screenshots/`, write the audit row, and the
  framework's consecutive-system-exception guard (`MaxConsecutiveSystemExceptions`)
  stops the run if a dependency is down.

Every path — success, BE, SE — writes exactly one audit row. No `Log Message`
filler: each transaction touches the services, OpenMRS, the file system and the
audit store.

---

## 9. Idempotency & re-runnability

- **Queue level:** Dispatcher uses unique **Reference = ReferralId**; re-dispatch
  doesn't duplicate items.
- **OpenMRS level:** §7.1 step 2 checks the `Source Document ID` obs before
  creating; a re-processed referral is a no-op (`action = exists`).
- **Artefacts:** extraction/decision JSON are overwritten per `ReferralId`
  (regenerable); the audit store is append-only (history preserved).
- Net: running Dispatcher + Performer twice over the same corpus yields the same
  OpenMRS state and the same final statuses — satisfying DoD §8.

---

## 10. Traceability — the 15 scenarios through the design

The Phase 3 oracles (`data/expected-outcomes/`) drive the Phase 8 acceptance.
Every scenario has a defined path through this design:

| Scenario(s) | `bot_decision` | Path | TX status |
|---|---|---|---|
| Bennett, Davies, Clarke (clean exact match) | AUTO_CREATE | §7.1 create+verify → `processed/` | Successful |
| Shaw (DOB mismatch), Hamilton (partial), Walsh (multiple), Reed (duplicate), Knight (2WW), Cole (safeguarding child), Fernandes/Osei (no-match), Owen (incomplete), Roberts (low-confidence) | HUMAN_REVIEW | review store → `review/` | Successful |
| REF-014 (not a referral) | BUSINESS_EXCEPTION | Throw BusinessRuleException → `failed/` | Failed (Business) |
| REF-015 (corrupt PDF) | SYSTEM_EXCEPTION | Throw Exception → retry → escalate → `failed/` | Failed (Application) |

This is the Phase 8 test matrix: 3 auto-create, 10 human-review, 1 BE, 1 SE.

---

## 11. What Phase 8 must build (handoff checklist)

1. `NHS.ReferralSafety.Dispatcher` per §3 (enumerate → Add Queue Item, unique ref).
2. `NHS.ReferralSafety.Performer` from the REFramework template; drop in
   `Config.xlsx`; customise the states/files in §6.
3. `Process.xaml` per §7, including the OpenMRS REST sequence §7.1.
4. The BE/SE wiring of §8 (this is the explicit Phase 7 gate).
5. Orchestrator setup: queue `NHS_Referrals`, credential asset
   `NHS_OpenMRS_Credential`.
6. Run the §10 matrix; expected: 3 processed, 10 review, 1 BE-failed, 1 SE-failed.

All upstream contracts (extraction JSON, decision JSON, OpenMRS calls) are already
built and tested in Phases 4–6 — Phase 8 is orchestration, not new business logic.
