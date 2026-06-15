# DTAC-inspired self-assessment

**Document type:** DTAC-inspired self-assessment (NHS Digital Technology Assessment Criteria)
**System:** Clinical Referral Safety Automation (UiPath REFramework + OpenMRS)
**Version:** 1.0 · **Date:** 2026-06-15

> ⚠️ **Portfolio simulation — synthetic data only. NOT a live NHS system.** This is *inspired
> by* the NHS DTAC to structure a self-assessment across its domains; it is **not** a submitted
> DTAC and confers no assurance. "Met" below means *demonstrated in this simulation*, with the
> gaps a real deployment would close stated explicitly.

## Summary

| DTAC domain | Self-assessment (simulation) | Evidence |
|---|---|---|
| A. Clinical safety | Demonstrated | DCB0129-inspired pack |
| B. Data protection | Demonstrated (synthetic) | DPIA |
| C. Technical security | Partially demonstrated | secrets handling, local-only |
| D. Interoperability | Demonstrated | REST/FHIR + schema |
| E. Usability & accessibility | Partially demonstrated | review worklist, reporting |

## A. Clinical safety (DCB0129 / DCB0160)

**Met (simulation).** A clinical risk management plan, a 12-hazard log with named controls and
control evidence, and a clinical safety case report exist and are machine-checked.

- Evidence: [`../clinical-safety/clinical-risk-management-plan.md`](../clinical-safety/clinical-risk-management-plan.md),
  [`../clinical-safety/hazard-log.csv`](../clinical-safety/hazard-log.csv),
  [`../clinical-safety/clinical-safety-case-report.md`](../clinical-safety/clinical-safety-case-report.md).
- **Gap for real use:** sign-off by a qualified, named Clinical Safety Officer; DCB0160
  operational controls (review-queue staffing/SLAs — hazard H-11).

## B. Data protection (UK GDPR / DPA 2018 / DSPT)

**Met (synthetic).** No real personal data; default processing is local and offline; no secrets
in the repo.

- Evidence: [`dpia.md`](dpia.md); `.env` git-ignored with [`../../.env.example`](../../.env.example);
  synthetic 999-range NHS numbers; the performer's synthetic-data guard.
- **Gap for real use:** completed DPIA against real flows, DSPT compliance, a data-processing
  agreement for any LLM provider, defined retention/erasure.

## C. Technical security

**Partially met.** Appropriate for a local synthetic simulation; production hardening is out of
scope by design.

- Demonstrated: secrets isolated to a git-ignored `.env` (never a UiPath asset or in code);
  services bind locally; OpenMRS runs in a local Docker network; structured, validated inputs
  reduce injection surface; append-only audit trail.
- **Gap for real use:** authentication/authorisation (Orchestrator RBAC, EMR access control),
  TLS in transit, encryption at rest, secret-vault management, penetration testing, vulnerability
  scanning, HA/DR. These are explicitly **out of scope** for the portfolio (see project scope §4).

## D. Interoperability

**Met (simulation).** The system integrates with a **real EMR** over standard interfaces rather
than a hand-faked store.

- Demonstrated: OpenMRS REST (and FHIR R4 available) integration; referrals modelled as a
  standard **Encounter + Obs** structure; a published JSON extraction schema
  ([`../../services/extraction-service/schema/extraction.schema.json`](../../services/extraction-service/schema/extraction.schema.json));
  Orchestrator queue contract with typed items.
- **Gap for real use:** mapping to national standards (e-RS, SNOMED CT coding, FHIR UK Core
  profiles) instead of the local OpenMRS concept dictionary.

## E. Usability & accessibility

**Partially met.** The human-in-the-loop and reporting surfaces exist; full accessibility is
not claimed for this simulation.

- Demonstrated: a reviewer worklist with mandatory identity + rationale capture
  ([`../../services/review-service/`](../../services/review-service/)); a reporting dashboard and
  Excel workbook ([`../../reports/`](../../reports/)) for operational oversight; clear,
  reason-coded outcomes.
- **Gap for real use:** a proper clinical review UI assessed to **WCAG 2.1 AA**, user research
  with referral administrators and clinicians, and training materials. The current reviewer
  interface is a CLI/REST stand-in for a clinical worklist.

## Overall

For a **synthetic portfolio simulation**, the system demonstrates the clinical-safety,
data-protection, interoperability, and human-oversight thinking the DTAC looks for, and is
explicit about the security, accessibility, and assurance work a real NHS deployment would
require before processing any real data.

## Related

[`dpia.md`](dpia.md) ·
[`../clinical-safety/`](../clinical-safety/) ·
[`../business/project-scope.md`](../business/project-scope.md)
