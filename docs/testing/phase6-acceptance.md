# Phase 6 — OpenMRS Workflow Mapping: Acceptance Record

**Date:** 2026-06-11
**Result:** ✅ PASS — the concrete OpenMRS referral update path runs end-to-end against a live instance: metadata created, AUTO_CREATE referrals **written and verified by re-read**, idempotent, with a working **live duplicate check**. Gate: **11/11**.

## What was built
`services/openmrs-workflow/` — the executable OpenMRS write/read path the bot uses for an `AUTO_CREATE_REFERRAL_RECORD` decision. **Real REST writes against a real EMR, verified by re-read — no log-message-only steps.**
- **`src/openmrs_client.py`** — stdlib REST client (Basic auth, same conventions as the Phase 2 seeder), `/session` readiness gate, NHS-number patient lookup.
- **`src/metadata.py`** — idempotently ensures the `Referral` encounter type + eight referral concepts; discovers datatype/class/location UUIDs from the live instance.
- **`src/referral_writer.py`** — `create_referral` (Encounter + Obs), `verify_referral` (re-read every field), `find_active_referrals` / `existing_referral_status` (live duplicate check), `write_referral_idempotent` (keyed on `REF-NNN`).
- **`setup_referral_metadata.py`**, **`seed_existing_referrals.py`**, **`run_referral_writeback.py`**, **`validate_acceptance.py`**.

## The referral data model
One `Referral` **Encounter** with one **Observation** per field (native Visit/Encounter/Obs, not a custom O3 form — fully verifiable over REST). Full specification, REST call shapes, and queries: [`docs/technical/openmrs-referral-workflow.md`](../technical/openmrs-referral-workflow.md).

Resolved metadata on this instance (cached to `config/referral-metadata.json`, gitignored):
- Encounter type `Referral`: `a049d86d-d937-4776-8ff0-5884c44a991e`
- Location (Outpatient Clinic): `44c3efb0-2583-4c80-a79e-1f756a03c0a1`
- Concept class `Question`: `8d491e50-c2cc-11de-8d13-0010c6dffd0f`
- Concepts: Speciality, Urgency, Reason, Referrer Name, Referrer Organisation, Status, Source Document ID, Suspected Cancer (Text ×7 + Boolean ×1).

## How to reproduce
```bash
docker compose -f openmrs-setup/docker-compose.yml up -d   # OpenMRS must be authenticated-ready
cd services/openmrs-workflow
python setup_referral_metadata.py    # idempotent: encounter type + concepts
python seed_existing_referrals.py    # Reed's pre-existing active Cardiology referral
python run_referral_writeback.py     # write + verify the 3 AUTO_CREATE referrals
python validate_acceptance.py        # exit 0 = all 11 checks pass
```

## Acceptance checks (all PASS — 11/11)
| Check | Evidence |
|---|---|
| OpenMRS REST authenticated | `/session` → `authenticated:true` |
| Referral encounter type exists | `a049d86d-d937-4776-8ff0-5884c44a991e` |
| All 8 referral concepts exist | speciality, urgency, reason, referrer_name, referrer_org, status, source_id, suspected_cancer |
| Reed has pre-existing `active:Cardiology` | seeded encounter `8f6915f8-…`; `existing_referral_status` → `active:Cardiology` |
| 3 AUTO_CREATE decisions to write | REF-001 Bennett, REF-002 Davies, REF-003 Clarke |
| Each written **and verified by re-read** | REF-001 `a5a6a87c-…`, REF-002 `f4eb76e2-…`, REF-003 `6b359d5a-…`; every field round-trips |
| Idempotent re-run | re-writing REF-001 → `exists`; encounter count stays 1 (no duplicate) |
| Live duplicate check | `find_active_referrals(Reed)` returns Cardiology → REF-007 would collide |
| Live == seed parity | live `existing_referral_status(Reed)` == seed file value Phase 5 used |

## Read-back evidence (REF-001, re-read live from OpenMRS)
```
encounter: a5a6a87c-b179-4484-a02a-250aa1c9c51f
type:      Referral
patient:   10001NG - Oliver Bennett
obs:
  Referral - Status              = active
  Referral - Referrer Name       = Dr Sarah Mills
  Referral - Referrer Organisation = The Grange Medical Practice
  Referral - Source Document ID  = REF-001
  Referral - Urgency             = Routine
  Referral - Reason              = ...exertional palpitations... routine cardiology review...
  Referral - Speciality          = Cardiology
```

## How this closes the Phase 5 duplicate dependency
Phase 5 read `existing_referral_status` from the synthetic seed file because the live referral encounters did not exist yet. Phase 6 creates them; `existing_referral_status(Reed)` queried **live** now returns `active:Cardiology` — identical to the seed value Phase 5 decided on. In Phase 8 the performer queries this live, so the duplicate check needs no seed file.

## Scope boundary (what Phase 6 does NOT do)
Phase 6 proves the **OpenMRS update path** in Python/REST. It does not yet run inside UiPath (Phase 8), and it only writes `AUTO_CREATE` referrals — `HUMAN_REVIEW` / `BUSINESS_EXCEPTION` / `SYSTEM_EXCEPTION` go to the review store / exception paths (Phase 9).

## Artefacts produced
- `services/openmrs-workflow/` (client, metadata, writer, CLIs, acceptance harness, README).
- Live OpenMRS records: Reed's pre-existing Cardiology referral + 3 created AUTO_CREATE referrals (in the docker volume).
- `config/referral-metadata.json` (generated, gitignored).

## Screenshots to capture (portfolio)
- `validate_acceptance.py` showing **GATE RESULT: 11/11**.
- The OpenMRS SPA showing Oliver Bennett's new `Referral` encounter (`http://localhost/openmrs/spa`).
- A re-read `GET /encounter/<uuid>` JSON showing the obs round-trip.

## Next — Phase 7
REFramework design spec: turn this executable path + the Phase 4/5 services into a buildable UiPath performer design (queue item schema, Config, assets, per-transaction state machine, Business vs System exception handling).
