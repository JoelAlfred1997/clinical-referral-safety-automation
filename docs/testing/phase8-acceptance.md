# Phase 8 — UiPath Build: Acceptance Record

**Date:** 2026-06-14
**Result:** ✅ PASS — the UiPath **Dispatcher + REFramework Performer** ran end-to-end
against a **real Orchestrator queue**, processed **all 15** synthetic referrals, created
clean referrals in **OpenMRS** (verified by re-read), routed every risky/ambiguous case to
**human review**, **detected the duplicate**, and separated **Business vs System exceptions**.
Gate: **15/15**, matching the Phase 3 oracles and the Phase 7 design matrix exactly.

## What was built
- **`uipath/NHS.ReferralSafety.Dispatcher/`** — blank-template process. `Main.xaml` enumerates
  `REF-*` files in `data/input-referrals/` and adds one **Add Queue Item** per referral to the
  `NHS_Referrals` queue (folder **Shared**), with **Reference = REF-NNN** (unique-reference
  idempotency) and typed `SpecificContent` (ReferralId, SourceFile, SourcePath, FileType,
  Synthetic, EnqueuedAtUtc).
- **`uipath/NHS.ReferralSafety.Performer/`** — official **REFramework 25.10.1** (Windows / VB).
  `Config.xlsx` carries the queue name, the three service URLs, OpenMRS REST root, the data
  folders, and the metadata path. `Framework/Process.xaml` is the orchestration:
  1. read queue-item fields + **synthetic-data guard**;
  2. **POST `/extract`** (HTTP Request) → save `data/extracted-json/REF-NNN.extracted.json`;
  3. **POST `/decide`** (source=`openmrs`) → save `data/decisions/REF-NNN.decision.json`,
     Deserialize JSON;
  4. write one **audit row** (every outcome);
  5. **Switch on `bot_decision`**: AUTO_CREATE → **POST `/writeback`** (OpenMRS create+verify)
     → move to `processed/`; HUMAN_REVIEW → append review row → move to `review/`;
     BUSINESS_EXCEPTION → move to `failed/` + `Throw BusinessRuleException`;
     SYSTEM_EXCEPTION → move to `failed/` + `Throw Exception`.
- **`services/openmrs-workflow/app.py`** — thin HTTP **`/writeback`** wrapper (port 8091) over
  the tested Phase 6 writer (find patient → idempotency on REF-NNN → clinical duplicate guard →
  create encounter+obs → **verify by re-read**). The escaping-sensitive EMR write is delegated to
  the proven Python writer; the bot orchestrates it as the third HTTP service (the documented
  Phase 7 "service wrapper" path).
- **`services/openmrs-workflow/reset_openmrs_baseline.py`** — voids all Referral encounters and
  re-seeds only Reed's pre-existing Cardiology referral → reproducible baseline for a clean run.

## Phase 8 wiring fix (closes the Phase 5/6 dependency)
`services/rules-engine/src/patient_repository.py` — `OpenmrsPatientRepository` previously reported
`existing_referral_status="none"` against live OpenMRS (documented gap). It now **queries the
patient's active Referral encounters live** (using the Phase 6 metadata UUIDs) and returns
`active:<Speciality>`. So the decision service (source=`openmrs`) the performer calls now detects
the duplicate, and **REF-007 routes to HUMAN_REVIEW** rather than being blocked at write time.

## Environment prerequisites established (for reproducibility)
- **.NET 8 SDK** (8.0.422) installed via winget; the bundled UiPath Studio host (`UiPathPlatform\
  Studio\26.0.195`) is runtime-only, so an `sdk` junction (and the `8.0.28` shared runtimes) were
  linked into it so `uip rpa validate` resolves the SDK; `dotnet` is prepended to PATH for
  `uip rpa build`/`run`.
- **UiPath Cloud** logged in (`uip login`) — org `skylarkautomations`, tenant `Technology_Tenant`.
- **Services** running: extraction `:8089`, decision `:8090`, writeback `:8091`. **OpenMRS** up.

## How to reproduce a clean run
```bash
# services: extraction(8089), decision(8090), writeback(8091) running; OpenMRS up; uip login done
git checkout -- data/input-referrals                      # restore corpus
rm -f data/{processed,review,failed}/REF-* data/review/review-store.csv data/audit/audit-log.csv
cd services/openmrs-workflow && python reset_openmrs_baseline.py   # baseline: only Reed active
# fresh queue:
uip or queues delete <key>; uip or queues create "NHS_Referrals" --folder-path Shared --enforce-unique-reference
export PATH="/c/Program Files/dotnet:$PATH"
cd uipath/NHS.ReferralSafety.Dispatcher && uip rpa run --file-path Main.xaml --skip-build   # 15 New
cd ../NHS.ReferralSafety.Performer   && uip rpa run --file-path Main.xaml --skip-build      # process 15
```

## Acceptance results (15/15)
| Scenario(s) | bot_decision | Queue status | Destination | Verified |
|---|---|---|---|---|
| REF-001 Bennett, REF-002 Davies, REF-003 Clarke | AUTO_CREATE | Successful (×3) | `processed/` | OpenMRS encounters created + **re-read verified** (Cardiology / Endocrinology / Respiratory Medicine) |
| REF-004 Shaw (DOB), 005 Hamilton (partial), 006 Walsh (multiple), **007 Reed (duplicate)**, 008 Knight (2WW), 009 Cole (safeguarding child), 010 Fernandes (no-match), 011 Osei (no-match), 012 Owen (incomplete), 013 Roberts (low-conf) | HUMAN_REVIEW | Successful (×10) | `review/` | 10 rows in `data/review/review-store.csv`; REF-007 reason `MATCH_EXACT\|DUPLICATE_REFERRAL` |
| REF-014 (not a referral) | BUSINESS_EXCEPTION | **Failed (Business)** | `failed/` | audit + queue Failed |
| REF-015 (corrupt PDF) | SYSTEM_EXCEPTION | **Failed (Application)** | `failed/` | audit + queue Failed |

**Counts:** queue 13 Successful + 2 Failed; files 3 processed / 10 review / 2 failed / 0 left;
audit log 15 rows; OpenMRS active referrals = Bennett, Davies, Clarke (new) + Reed (pre-existing).

## BE vs System exception separation (demonstrated live)
- **HUMAN_REVIEW is a success** (queue Successful) — routing a risky case to a human is the safe
  designed outcome, not a failure. 10 referrals.
- **BUSINESS_EXCEPTION** (REF-014) → `BusinessRuleException` → queue **Failed (Business)**, no retry.
- **SYSTEM_EXCEPTION** (REF-015) → `Exception` → queue **Failed (Application)**; `MaxRetryNumber=0`
  and `MaxConsecutiveSystemExceptions=0` so it neither retries nor aborts the run.
- Operational HTTP/OpenMRS failures throw `Exception` (system) — same path.

## Idempotency
Queue Reference = REF-NNN with **unique-reference enforcement** (no double-enqueue). The writeback
is keyed on the `Referral - Source Document ID` obs (REF-NNN) → re-processing returns `exists`, no
duplicate OpenMRS record. Re-runs are clean after `reset_openmrs_baseline.py` + a fresh queue.

## Screenshots to capture (portfolio)
- Orchestrator `NHS_Referrals` queue showing 13 Successful + 2 Failed.
- The OpenMRS SPA showing Oliver Bennett's new `Referral` encounter.
- `data/audit/audit-log.csv` (15 rows) and `data/review/review-store.csv` (10 rows).
- The `Process.xaml` Switch (the BE/SE routing) in Studio.

## Scope boundary (what Phase 8 does NOT do)
Human-review decisions are recorded (PENDING) but feeding a reviewer decision back into the outcome
is **Phase 9**. Reporting/dashboard is **Phase 10**. The audit/review stores are CSV here (SQLite in
Phase 9). The OpenMRS write is performed by the Phase 6 writer behind the `/writeback` HTTP service.

## Next — Phase 9
Human-in-the-loop review: a real store where a reviewer decision changes the final outcome, with
the bot re-reading the decision and auditing it.
