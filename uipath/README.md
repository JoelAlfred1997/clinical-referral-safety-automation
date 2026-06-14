# `uipath/` — UiPath REFramework solution

> Portfolio simulation. Synthetic data only. OpenMRS is a mock EPR/EMR.

This area holds the UiPath **Dispatcher + REFramework Performer + ReviewResolver**
for the Clinical Referral Safety Automation, plus the design contract they are built from.

## Contents

| Path | What | Phase |
|---|---|---|
| [`design/reframework-design-spec.md`](design/reframework-design-spec.md) | The buildable design: queue schema, Config workbook, Assets/Credentials, per-transaction state machine, **Business- vs System-Exception** policy, scenario traceability. | 7 ✅ |
| [`design/Config.xlsx`](design/Config.xlsx) | The REFramework Config workbook (Settings / Constants / Assets) the Performer ships with. | 7 ✅ |
| `NHS.ReferralSafety.Dispatcher/` | Studio project — enumerate referrals → queue items. | 8 ✅ |
| `NHS.ReferralSafety.Performer/` | Studio project — REFramework performer. | 8 ✅ |
| `NHS.ReferralSafety.ReviewResolver/` | Studio project — re-reads human-review decisions and applies each outcome (POST `/resolve`). | 9 ✅ |

## How it fits together

The Performer orchestrates services that are **already built and tested**:

- **Phase 4** extraction service — `services/extraction-service/` (HTTP `:8089`).
- **Phase 5** decision engine — `services/rules-engine/` (HTTP `:8090`).
- **Phase 6** OpenMRS write/verify — `services/openmrs-workflow/` (REST), with
  resolved UUIDs in `services/openmrs-workflow/config/referral-metadata.json`.
- **Phase 9** human-in-the-loop review store + resolver — `services/review-service/`
  (SQLite + HTTP `:8092`). The **ReviewResolver** process POSTs `/resolve`; the
  service applies each clinician decision (create in OpenMRS / no record), audits,
  idempotently.

Phase 8 is orchestration only — no new business logic. Phase 9 adds the review loop
that lets a clinician's decision change the final outcome. Start from
[`design/reframework-design-spec.md`](design/reframework-design-spec.md) §11
(handoff checklist).
