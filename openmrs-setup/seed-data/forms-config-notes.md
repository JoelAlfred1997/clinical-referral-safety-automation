# Forms & Configuration Notes (preview — finalised in Phase 6)

How referral data is represented in OpenMRS and what we configure to support it.
**Synthetic data only.**

## 1. Identifier type for synthetic NHS numbers (Phase 2 dependency)

OpenMRS ships with an **OpenMRS ID** identifier type (auto-generated, Luhn check). Our
synthetic patients also need an NHS-style identifier so the bot can match on it.

Plan (decide/execute in Phase 2):
- Add a custom **Patient Identifier Type**: name `Synthetic NHS Number`, format note
  "999-test range, Modulus-11 valid, SYNTHETIC — not a real NHS number".
- Configure via legacy admin UI: `http://localhost/openmrs` →
  **Administration → Manage Patient Identifier Types → Add**, or via REST
  `POST /ws/rest/v1/patientidentifiertype`.
- The bot's patient search queries this identifier first (`?q=<nhs>`), then falls back to
  demographics (surname + DOB + postcode).

## 2. Encounter type for referrals

- Add **Encounter Type**: name `Referral`, description "Synthetic inbound referral record".
- Admin UI: **Administration → Manage Encounter Types → Add**, or REST
  `POST /ws/rest/v1/encountertype`.
- Each processed referral = one `Referral` encounter under a Visit for the matched patient.

## 3. Concepts for referral observations

Each referral field becomes an Observation bound to a Concept. OpenMRS demo content already
includes many concepts; where a suitable one is missing we add it
(**Administration → Manage Concepts** or REST `POST /ws/rest/v1/concept`).

| Referral field | Obs concept (planned) | Datatype |
|---|---|---|
| Speciality / requested service | "Referral speciality" | Coded or Text |
| Referral reason | "Reason for referral" | Text |
| Urgency | "Referral urgency" (Routine / Urgent / 2WW suspected cancer) | Coded |
| Referrer name | "Referrer name" | Text |
| Referrer organisation | "Referrer organisation" | Text |
| Suspected-cancer flag | "Suspected cancer" | Boolean |
| Clinical summary | "Clinical summary / referral note" | Text (long) |

Exact concept UUIDs are captured in `uipath/.../workflow-design.md` during Phase 6 and
referenced by the bot from Config, not hard-coded in selectors.

## 4. Why structures, not a custom form

We model referrals with **native Visit/Encounter/Obs** rather than building a custom O3
form, because:
- It exercises the real OpenMRS clinical data model (better interview story).
- It is fully reachable and verifiable via REST (reliable bot writes + re-read checks).
- It avoids coupling the project to O3 form-engine/RFE schema churn.

A custom O3 clinical form is an **optional later enhancement** for nicer UI screenshots,
not a Phase-1–8 requirement.

## 5. FHIR option (noted, not required)

OpenMRS exposes FHIR R4 at `/openmrs/ws/fhir2/R4`. A referral could alternatively be a FHIR
**ServiceRequest**. We default to the REST Encounter/Obs model for simplicity and
verifiability; FHIR ServiceRequest is recorded here as a credible alternative to mention in
interviews.
