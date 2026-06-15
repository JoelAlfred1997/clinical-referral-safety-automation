# Information governance pack

> ⚠️ **Portfolio simulation — synthetic data only. NOT a live NHS system.** No real or
> identifiable personal data is processed. These artefacts are *inspired by* the ICO/NHS DPIA
> process and the NHS DTAC to demonstrate information-governance thinking; they are not
> submitted assessments.

Information-governance artefacts for the Clinical Referral Safety Automation, written to pair
with the [clinical-safety pack](../clinical-safety/).

## Contents

| Document | What it is |
|---|---|
| [`dpia.md`](dpia.md) | DPIA-inspired assessment: nature of processing, data flow, key data-protection risks + mitigations, data minimisation, outcome. States the real-deployment position alongside the actual (synthetic) one. |
| [`dtac-assessment.md`](dtac-assessment.md) | DTAC-inspired self-assessment across the five domains (clinical safety, data protection, technical security, interoperability, usability), each with evidence and the gap a real deployment would close. |

## The IG headline

The **default path is fully local and offline** — the deterministic extractor sends nothing off
the machine; the optional LLM path is opt-in and, for real PII, would need an IG-approved model.
**No secrets are committed** (`.env` is git-ignored; `.env.example` ships placeholders; the LLM
key is never a UiPath asset). All data is **synthetic**, using reserved 999-range NHS numbers
with a `SYNTHETIC` tag, and the bot refuses any non-synthetic input.

## Related

[`../clinical-safety/`](../clinical-safety/) · [`../business/project-scope.md`](../business/project-scope.md)
