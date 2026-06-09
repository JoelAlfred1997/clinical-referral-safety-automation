# Phase 1 — OpenMRS Local Setup: Acceptance Record

**Date:** 2026-06-09
**Result:** ✅ PASS — OpenMRS 3 reference application running locally via Docker.

## Environment
- Docker Desktop (WSL2 backend) on Windows 11 Home, build 26200.
- WSL repaired from `Wsl/CallMsi/Install/REGDB_E_CLASSNOTREG` by updating WSL → v2.7.3.0.
- Docker engine Server 29.5.3.
- Stack: `openmrs-setup` compose project — gateway / frontend / backend / db (MariaDB 10.11.7).
- Images: `openmrs/openmrs-reference-application-3-{gateway,frontend,backend}:qa`.

## First-boot note
First boot ran the OpenMRS install wizard (CREATE_TABLES → ADD_CORE_DATA →
UPDATE_TO_LATEST) then generated reference demo data — **~45 min, CPU-bound, one-time**.
Subsequent `docker compose up -d` is fast (data persisted in `openmrs-data` / `db-data`
volumes). Container `health: healthy` appears BEFORE the app is truly ready — use the REST
`/session` check below as the real readiness gate, not the container healthcheck.

## Acceptance checks (all PASS)
| Criterion | Evidence |
|---|---|
| OpenMRS runs locally | 4 containers Up/healthy |
| Can log in | REST `/ws/rest/v1/session` → `authenticated: true`, user admin (System Developer, Provider) |
| Can search patients | `?q=John` → 1, `?q=Smith` → 2 (single letters below search threshold → 0; expected) |
| Demo patients exist | FHIR `Patient?_summary=count` → **50** |
| REST API usable by bot | 200 on session, patient, encountertype, patientidentifiertype |
| FHIR available (alt path) | `ws/fhir2/R4/metadata` → 200 |
| Update path identified | Referral = Visit → Encounter (type "Referral") → Obs; create via REST, verify by re-read |

## State relevant to later phases
- **Identifier types present:** OpenMRS ID, ID Card, Legacy ID, Old Identification Number,
  OpenMRS Identification Number, SSN. **No NHS-number type yet** → add `Synthetic NHS Number`
  in Phase 2.
- **Encounter types:** 19 present; **no "Referral" type yet** → add in Phase 2/6.
- **Sample patients for UI screenshots:** `Mark Smith` (id 100004N, M, 2015-06-14),
  `Mary Smith` (id 10000F1, F, 1982-02-01).

## Endpoints
- O3 SPA: http://localhost/openmrs/spa
- Legacy admin UI: http://localhost/openmrs
- REST base: http://localhost/openmrs/ws/rest/v1
- FHIR R4: http://localhost/openmrs/ws/fhir2/R4
- Login: admin / Admin123
