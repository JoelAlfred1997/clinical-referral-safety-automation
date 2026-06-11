# OpenMRS Referral Workflow — concrete, executable update path (Phase 6)

> Portfolio simulation. **Synthetic data only.** OpenMRS is a mock EPR/EMR.
> This document specifies the *executable* path the bot uses to create and verify
> a referral record — real REST writes, verified by re-read, no log-message-only
> steps. Implemented in `services/openmrs-workflow/`.

---

## 1. Where this sits in the flow

Architecture steps 8–12 for a referral that the Phase 5 engine decided is
`AUTO_CREATE_REFERRAL_RECORD`:

```
decision (Phase 5)  ──▶  find patient in OpenMRS (by synthetic NHS number)
                    ──▶  live duplicate guard (query active Referral encounters)
                    ──▶  CREATE Referral encounter + observations (REST POST)
                    ──▶  VERIFY by re-reading the encounter (REST GET)
                    ──▶  (Phase 8) move file to processed/, write audit row
```

`HUMAN_REVIEW_REQUIRED`, `BUSINESS_EXCEPTION` and `SYSTEM_EXCEPTION` decisions are
**not** written to OpenMRS — they go to the review store / exception paths
(Phase 9).

## 2. Data model — native Visit/Encounter/Obs

A referral is **one `Referral` Encounter** with **one Observation per field**. We
use the native clinical model (not a custom O3 form) because it exercises the real
OpenMRS data model and is fully reachable + verifiable over REST.

| Field key | Concept (fully-specified name) | Datatype | Populated from |
|---|---|---|---|
| `speciality` | Referral - Speciality | Text | extraction `specialty` |
| `urgency` | Referral - Urgency | Text | extraction `priority` |
| `reason` | Referral - Reason | Text | extraction `reason_for_referral` |
| `referrer_name` | Referral - Referrer Name | Text | extraction `referring_clinician` |
| `referrer_org` | Referral - Referrer Organisation | Text | extraction `referring_practice` |
| `status` | Referral - Status | Text | workflow — `active` |
| `source_id` | Referral - Source Document ID | Text | `REF-NNN` (idempotency key) |
| `suspected_cancer` | Referral - Suspected Cancer | Boolean | extraction signal (only when true) |

Concept **datatype** (Text/Boolean), concept **class** (Question) and the clinic
**location** are discovered from the live instance; the `Referral` encounter type
and the eight concepts are created if missing. All resolved UUIDs are cached to
`services/openmrs-workflow/config/referral-metadata.json` (generated, gitignored)
so nothing instance-specific is hard-coded in the bot.

## 3. The REST calls

### 3.1 Ensure metadata (idempotent, `setup_referral_metadata.py`)
- `GET /encountertype?q=Referral` → reuse, else `POST /encountertype {name, description}`.
- `GET /conceptdatatype?q=Text|Boolean`, `GET /conceptclass?q=Question` → resolve UUIDs.
- per concept: `GET /concept?q=<name>` (exact display match) → reuse, else
  `POST /concept {names:[{name, conceptNameType:FULLY_SPECIFIED}], datatype, conceptClass}`.

### 3.2 Find the patient
- `GET /patient?q=<nhs>&v=full` → the patient whose `Synthetic NHS Number` identifier equals the referral's NHS number.

### 3.3 Live duplicate guard
- `GET /encounter?patient=<uuid>&encounterType=<referralType>&v=custom:(uuid,encounterDatetime,voided,obs:(uuid,concept:(uuid,display),value))`
- A referral is **active** if its `Referral - Status` obs is `active` (and not voided). `existing_referral_status(patient)` returns `active:<Speciality>` for the first active referral, else `none` — the live equivalent of the seed value the Phase 5 engine consumed.

### 3.4 Create the encounter
```http
POST /encounter
{
  "patient":          "<patient uuid>",
  "encounterType":    "<Referral type uuid>",
  "location":         "<Outpatient Clinic uuid>",
  "encounterDatetime":"<ISO datetime with offset>",
  "obs": [
    {"concept": "<Referral - Speciality uuid>",        "value": "Cardiology"},
    {"concept": "<Referral - Urgency uuid>",           "value": "Routine"},
    {"concept": "<Referral - Reason uuid>",            "value": "..."},
    {"concept": "<Referral - Referrer Name uuid>",     "value": "Dr ..."},
    {"concept": "<Referral - Referrer Organisation uuid>", "value": "... Surgery"},
    {"concept": "<Referral - Status uuid>",            "value": "active"},
    {"concept": "<Referral - Source Document ID uuid>","value": "REF-001"}
  ]
}
```
`encounterDatetime` is the processing time (server-relative "now"), never a future
date, so it is always accepted.

### 3.5 Verify by re-read
- `GET /encounter/<uuid>?v=custom:(...obs...)` → decode the obs back into field keys and assert every written field round-trips. Only then is the referral considered "created".

## 4. Idempotency & duplicates

- **Idempotency key:** the `Referral - Source Document ID` obs (`REF-NNN`). Before
  creating, `find_by_source_id(patient, REF-NNN)` is checked; if present, the write
  is a no-op (`action = exists`). Re-running the whole pipeline creates **no**
  duplicate OpenMRS records.
- **Duplicate referral (clinical):** a *different* referral for a patient who
  already has an **active** referral in the **same speciality**. Detected by
  `find_active_referrals`. This is the live realisation of the REF-007 scenario —
  Arthur Reed (`9990000336`) has a pre-existing `active:Cardiology` referral
  (seeded by `seed_existing_referrals.py`), so a new Cardiology referral collides.

## 5. Why this closes the Phase 5 dependency

Phase 5 read `existing_referral_status` from the synthetic seed file because the
live referral encounters did not exist yet. Phase 6 creates them; the same fact is
now queryable live and returns the identical value, so in Phase 8 the performer
needs no seed file for the duplicate check.

## 6. Alternatives considered

- **FHIR ServiceRequest** (`/ws/fhir2/R4`) — a credible alternative representation;
  we default to the REST Encounter/Obs model for simplicity and verifiability.
- **Custom O3 clinical form** — optional later enhancement for nicer UI
  screenshots; not required for the Phase 1–8 write/verify path.

## 7. Evidence

`services/openmrs-workflow/validate_acceptance.py` exercises the whole path against
a live OpenMRS. Run results and the per-check gate are recorded in
[`docs/testing/phase6-acceptance.md`](../testing/phase6-acceptance.md).
