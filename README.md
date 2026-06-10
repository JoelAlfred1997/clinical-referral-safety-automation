# Clinical Referral Safety Automation
### UiPath REFramework · OpenMRS EMR · Synthetic Data · AI-assisted Extraction · Clinical Safety Controls

> ⚠️ **Portfolio simulation — synthetic data only. Not a live NHS system.**
> OpenMRS is used as a **mock EPR/EMR**. AI assists extraction; it does **not** make
> clinical decisions. All uncertain, urgent, incomplete, duplicate, or patient-match-risk
> cases are routed to human review.

A serious, end-to-end Intelligent Automation project built to NHS RPA / IA standards.
A synthetic referral letter arrives → the UiPath bot extracts it (LLM + deterministic
fallback), validates the patient against OpenMRS, checks completeness, patient-match risk
and duplicate risk, applies clinical-safety rules, creates a referral record in OpenMRS
for safe cases, escalates risky cases to a real human-review store, writes a full audit
trail, files the document, and produces reporting evidence.

---

## Capabilities demonstrated

REFramework · Orchestrator queues · config-driven design · Assets & credentials ·
browser + REST automation against a real EMR · PDF/text extraction · AI-assisted
(LLM) extraction with JSON-schema validation · deterministic regex fallback ·
patient matching · duplicate-referral detection · rule-based clinical-safety decisions ·
human-in-the-loop review · append-only audit logging · exception handling & retries ·
DCB0129 / DCB0160 / DTAC / DPIA-inspired clinical-safety governance.

## Repository layout

```
/openmrs-setup        Docker + setup notes, seed data, forms config
/uipath               REFramework project + design specs (queue, config, assets, workflows)
/data                 input-referrals, processed, failed, review, extracted-json, synthetic-patients
/services             extraction-service, audit-service, review-service (optional)
/docs                 business, technical, clinical-safety, information-governance, testing, cv-linkedin
/reports              Excel output + dashboard
```

## Status

Building phase by phase. See [`docs/business/project-scope.md`](docs/business/project-scope.md)
for the roadmap and Definition of Done.

| Phase | Status |
|---|---|
| 0 — Scope & architecture | ✅ complete |
| 1 — OpenMRS local setup | ✅ complete (50 demo patients, REST+FHIR verified) |
| 2 — Synthetic patient data | ✅ complete (32 synthetic patients, 999-range NHS nums, idempotent seeder) |
| 3 — Synthetic referral documents | ✅ complete (15 referrals + expected-outcome oracles, all scenarios & 4 bot decisions) |
| 4 — Extraction service | ✅ complete (LLM + regex + schema validation; 15/15 extract correctly vs oracles) |
| 5 — Rules & safety decision engine | ⬜ next |
| 6–13 | ⬜ pending |

## Key documents

- Architecture — [`docs/technical/architecture.md`](docs/technical/architecture.md)
- Project scope & DoD — [`docs/business/project-scope.md`](docs/business/project-scope.md)
- Clinical safety boundary — [`docs/clinical-safety/safety-boundary-statement.md`](docs/clinical-safety/safety-boundary-statement.md)

## Safety & data

100% synthetic data. Synthetic NHS-style numbers use the reserved 999-test range and are
tagged `SYNTHETIC`. No secrets in the repo — see [`.env.example`](.env.example).
