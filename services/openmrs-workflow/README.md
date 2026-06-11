# OpenMRS referral workflow (Phase 6)

> **Synthetic data only.** The concrete, executable OpenMRS update path the bot
> uses once a referral has been **decided** (Phase 5). Real REST writes against a
> real EMR, verified by re-read — **no log-message-only steps.**

This component maps a decided referral onto the native OpenMRS clinical data
model and proves the write/read path end-to-end. It is what Phase 8 (the UiPath
performer) calls for an `AUTO_CREATE_REFERRAL_RECORD` decision.

## The referral data model (native Visit/Encounter/Obs, not a custom form)

A referral is **one `Referral` Encounter** carrying **one Observation per field**,
so it is fully reachable and verifiable over REST:

| Field key | Concept | Datatype | Source |
|---|---|---|---|
| `speciality` | Referral - Speciality | Text | extraction `specialty` |
| `urgency` | Referral - Urgency | Text | extraction `priority` |
| `reason` | Referral - Reason | Text | extraction `reason_for_referral` |
| `referrer_name` | Referral - Referrer Name | Text | extraction `referring_clinician` |
| `referrer_org` | Referral - Referrer Organisation | Text | extraction `referring_practice` |
| `status` | Referral - Status | Text | workflow (`active`) |
| `source_id` | Referral - Source Document ID | Text | `REF-NNN` (idempotency key) |
| `suspected_cancer` | Referral - Suspected Cancer | Boolean | extraction signal |

The encounter type, concepts, datatype/class and clinic location are **discovered
or created idempotently** (`setup_referral_metadata.py`) and cached to
`config/referral-metadata.json` — nothing instance-specific is hard-coded.

## What it does

- **`src/openmrs_client.py`** — stdlib REST client (Basic auth, same conventions as the Phase 2 seeder) + the `/session` readiness gate and NHS-number patient lookup.
- **`src/metadata.py`** — idempotently ensures the `Referral` encounter type and the eight referral concepts exist; discovers datatype/class/location UUIDs.
- **`src/referral_writer.py`** — `create_referral` (Encounter + Obs), `verify_referral` (re-read every field), `find_active_referrals` / `existing_referral_status` (the **live duplicate check**), and `write_referral_idempotent` (keyed on `REF-NNN`).
- **`setup_referral_metadata.py`** — one-time metadata setup (idempotent).
- **`seed_existing_referrals.py`** — seeds the pre-existing active referrals from the patient seed file (Arthur Reed `9990000336`, `active:Cardiology`) so the duplicate scenario (REF-007) is detectable live.
- **`run_referral_writeback.py`** — for each `AUTO_CREATE` decision: find patient → live duplicate guard → write → verify.
- **`validate_acceptance.py`** — the Phase 6 acceptance harness.

## Run it

```bash
# 0. OpenMRS must be up (first boot is slow; data persists in the docker volume)
docker compose -f openmrs-setup/docker-compose.yml up -d

cd services/openmrs-workflow
python setup_referral_metadata.py     # create/resolve encounter type + concepts (idempotent)
python seed_existing_referrals.py     # seed Reed's pre-existing active Cardiology referral
python run_referral_writeback.py      # write + verify the AUTO_CREATE referrals (REF-001/002/003)

# Phase 6 ACCEPTANCE: end-to-end, self-contained (re-extracts, re-decides, writes, verifies)
python validate_acceptance.py         # exit 0 = all checks pass
```

All scripts are **idempotent** — re-running creates no duplicate OpenMRS records
(the `source_id` observation is the key).

## How this closes the Phase 5 duplicate dependency

The Phase 5 decision engine read `existing_referral_status` from the synthetic
seed file (the `local-seed` backend) because the live referral encounters did not
exist yet. Phase 6 creates them: after `seed_existing_referrals.py`,
`existing_referral_status(Reed)` queried **live from OpenMRS** returns
`active:Cardiology` — identical to the seed value Phase 5 decided on. In Phase 8
the performer queries this live, so the duplicate check needs no seed file.

## Verification & evidence

`validate_acceptance.py` asserts: metadata exists, Reed's pre-existing referral is
present and queryable, each `AUTO_CREATE` referral is written **and verified by
re-read**, the write is idempotent (no duplicate on re-run), the live duplicate
check sees Reed's Cardiology referral, and the live status matches the seed Phase 5
used. Evidence: [`docs/testing/phase6-acceptance.md`](../../docs/testing/phase6-acceptance.md).
The concrete update path (encounter/obs shapes, UUIDs, queries) is documented in
[`docs/technical/openmrs-referral-workflow.md`](../../docs/technical/openmrs-referral-workflow.md).
```
src/openmrs_client.py        Stdlib REST client + readiness gate + patient lookup
src/metadata.py              Idempotent encounter type + concept setup (UUID discovery)
src/referral_writer.py       create / verify / duplicate-query / idempotent write
setup_referral_metadata.py   CLI: ensure metadata -> config/referral-metadata.json
seed_existing_referrals.py   CLI: seed pre-existing active referrals (duplicate fixtures)
run_referral_writeback.py    CLI: realise AUTO_CREATE decisions as OpenMRS records
validate_acceptance.py       Phase 6 acceptance harness
config/referral-metadata.json  Cached resolved UUIDs (generated; gitignored)
```
