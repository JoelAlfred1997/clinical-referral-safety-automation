# Clinical Safety Boundary Statement

**This is a portfolio simulation. It is not a live NHS system and processes only
synthetic data.**

## Core boundary

1. **No real patient data.** All patients, referrals, NHS-style numbers, and clinical
   details are synthetic and labelled as such. Synthetic NHS numbers use the reserved
   **999-test range** and carry a `SYNTHETIC` tag.

2. **AI does not make clinical decisions.** The LLM only assists with text extraction,
   summarisation, and *suggested* classification. Its output is schema-validated and can
   only *propose*. Every safety-sensitive outcome is owned by **deterministic rules** and,
   where there is any doubt, by a **human reviewer**.

3. **Mandatory human review.** The following always route to a human and never auto-create
   a record:
   - urgent / suspected-cancer / red-flag clinical content
   - incomplete referrals (missing mandatory fields)
   - patient-match risk (DOB mismatch, partial match, multiple candidates, no match)
   - duplicate-referral risk
   - low extraction confidence
   - any unhandled ambiguity

4. **Auditable by design.** Every bot action records who/what/before/after/when and the
   decision reason code. Nothing safety-relevant happens without a trace.

5. **Fail safe, not fail open.** On uncertainty or error, the bot escalates or raises an
   exception — it never silently proceeds to write a clinical record.

## Explicit non-claims

- This is **not** assured or certified clinical software.
- DCB0129 / DCB0160 / DTAC / DPIA artefacts are **inspired by** those standards to
  demonstrate clinical-safety thinking; they are **not** formal regulatory submissions.
- The bot performs **no clinical triage as a medical act** — it routes; clinicians decide.
