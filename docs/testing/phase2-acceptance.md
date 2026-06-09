# Phase 2 — Synthetic Patient Data: Acceptance Record

**Date:** 2026-06-09
**Result:** ✅ PASS — 32 synthetic patients seeded into OpenMRS (idempotent, repeatable).

## What was built
- Deterministic generator + idempotent REST seeder (Python stdlib, no pip deps).
- A custom `Synthetic NHS Number` patient identifier type
  (`b3f1cb43-540d-4f2e-b4a5-2014a435cf30`).
- 34 curated patients (32 seeded, 2 reserved as no-match fixtures).

## Synthetic-by-construction guarantees
- NHS numbers: reserved **999 test range**, **valid Modulus-11 check digit** (algorithm in
  `generate_patients.py::nhs_check_digit`).
- Phones: Ofcom reserved fictional **07700 900xxx**.

## Acceptance checks (all PASS)
| Criterion | Evidence |
|---|---|
| ≥30 synthetic patients in OpenMRS | 32 created (`failed=0`); searchable |
| Patient search works | `q=9990000018`→1; `q=Walsh`→2; `q=Hamilton/Shaw/Reed/Bennett`→1 each |
| Each patient has required + NHS identifier | Oliver Bennett: OpenMRS ID `10001NG` (preferred) + Synthetic NHS Number `9990000018` |
| Demographics stored for matching | DOB 1979-04-12, gender M, postcode LS6 2AF persisted |
| Idempotent / re-runnable | 2nd run: `created=0, skipped=32, failed=0` |
| Match-scenario fixtures exist | exact, dob_mismatch, partial, multiple-candidate (Walsh×2), duplicate-target, no-match |

## Scenario fixtures (drive Phase 5 matching tests)
| Scenario | Count | Example |
|---|---|---|
| standard (exact-match pool) | 27 | Oliver Bennett `9990000018` |
| dob_mismatch_target | 1 | Ruby Shaw `9990000271` |
| partial_match_target | 1 | Leo Hamilton `9990000298` |
| multiple_candidate (same surname+DOB) | 2 | Helen Walsh `9990000301` / `9990000328` (both 1975-03-12) |
| duplicate_target (pre-existing referral seeded in Phase 6/8) | 1 | Arthur Reed `9990000336`, existing_referral_status=active:Cardiology |
| no_match (reserved, NOT in OpenMRS) | 2 | Maria Fernandes `9990000360`, Ibrahim Osei `9990000379` |

## How to reproduce
```powershell
cd openmrs-setup\seed-data
python generate_patients.py      # writes data/synthetic-patients/*.json/.csv
python seed_openmrs.py           # creates identifier type + patients (idempotent)
```

## Key OpenMRS UUIDs (for later phases)
- Synthetic NHS Number type: `b3f1cb43-540d-4f2e-b4a5-2014a435cf30`
- OpenMRS ID type: `05a29f94-c0ed-11e2-94be-8c13b969e334`
- idgen source (Generator for OpenMRS ID): `8549f706-7e85-4c1d-9424-217d50a2988b`
- Location (Outpatient Clinic): `44c3efb0-2583-4c80-a79e-1f756a03c0a1`
- Telephone Number attribute: `14d4f066-15f5-102d-96e4-000c29c2a5d7`

## Note / deferred
- The `duplicate_target` patient needs a **pre-existing Referral encounter** to be detectable
  as a duplicate. That encounter is seeded in Phase 6/8, once the `Referral` encounter type and
  referral concepts exist. Tracked, not forgotten.
