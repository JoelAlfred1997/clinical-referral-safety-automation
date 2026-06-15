# Data Protection Impact Assessment (DPIA)

**Document type:** DPIA-inspired assessment (UK GDPR Art. 35 / DPA 2018)
**System:** Clinical Referral Safety Automation (UiPath REFramework + OpenMRS)
**Version:** 1.0 · **Date:** 2026-06-15

> ⚠️ **Portfolio simulation — synthetic data only. NOT a live NHS system.** No real or
> identifiable personal data is processed at any point. This DPIA is *inspired by* the ICO/NHS
> DPIA process to demonstrate information-governance thinking; it is not a completed DPIA for a
> live service. Where it states a lawful basis or controller, that is **illustrative of what a
> real deployment would require** — it does not apply here because the data is synthetic.

## 1. Need for a DPIA

A real version of this system would process **special-category health data** at scale, use
**automated decision-making with a human-in-the-loop**, and optionally an **AI/LLM** component —
each of which independently indicates a DPIA. This document records the assessment as it would
be framed, then states the actual (synthetic) position.

## 2. Nature of the processing

| Aspect | Real deployment (illustrative) | This simulation (actual) |
|---|---|---|
| Controller | The NHS provider organisation | n/a — no personal data |
| Processors | UiPath Orchestrator/robots; the EMR; any LLM provider | Local-only; synthetic data |
| Data subjects | Patients referred for care | **Synthetic** patients only |
| Data categories | Name, DOB, NHS number, demographics, **clinical referral content** | Same *shape*, but fabricated |
| Volume | High, continuous | 15 fixed synthetic scenarios |
| Lawful basis | Art. 6(1)(e) public task; Art. 9(2)(h) health/social care | **Not applicable** (synthetic) |

## 3. Data flow

```
referral file (synthetic)
   → Extraction service  (:8089, local)  → extracted JSON (schema-validated)
   → Decision engine     (:8090, local)  → decision JSON
   → [auto] Writeback     (:8091, local)  → OpenMRS (local Docker, REST)
   → [risky] Review store (SQLite, local) → reviewer decision → Writeback → OpenMRS
   → Audit log (local CSV) + Reporting (local Excel/HTML)
```

Every component runs **locally** on the developer machine: the three Python services, the
SQLite review store, the audit log, and OpenMRS (Docker, `localhost`). **No data leaves the
machine on the default path.**

## 4. Key data-protection risks & mitigations

| # | Risk | In this simulation | Mitigation (now / for real use) |
|---|---|---|---|
| DP-1 | Real patient data is ingested | Prevented by design | Synthetic-only corpus; NHS numbers in the reserved **999 test range** with a `SYNTHETIC` tag; the performer's **synthetic-data guard** rejects any non-synthetic queue item (`Process.xaml`). For real use: formal data-flow approval + DPIA sign-off. |
| DP-2 | Referral text sent to a third-party LLM | Not on the default path | The **default extractor is deterministic regex — fully offline, nothing leaves the machine**. The LLM path is opt-in (`USE_LLM=true`); for real PII it must be an IG-approved/in-house model with a data-processing agreement. |
| DP-3 | Secrets / API keys leak via the repo | Controlled | `.env` is git-ignored; `.env.example` ships placeholders; the **LLM key lives only in the service `.env`, never as a UiPath asset or in code** (see `.gitignore`, `.env.example`). |
| DP-4 | Excessive data retention | Low (synthetic) | Extraction/decision/runtime outputs are git-ignored runtime artefacts, regenerable and disposable; only synthetic fixtures and committed evidence persist. For real use: define retention/erasure per records-management policy. |
| DP-5 | Unauthorised access / no accountability | Mitigated for audit | Every action is logged with who/what/when (append-only audit + reviewer identity). For real use: Orchestrator RBAC, EMR access control, encryption in transit/at rest, DSPT compliance. |
| DP-6 | Automated decision-making affecting individuals (Art. 22) | Addressed by design | The system never makes a final clinical decision autonomously — deterministic rules + a **human-in-the-loop** own every risky outcome (see the clinical-safety pack). |

## 5. Data minimisation & subject rights (for real use)

- Extract and store **only** the fields needed to match and route a referral (the schema is
  explicit and validated).
- Subject-access / rectification / erasure would be served from the EMR of record, not the
  automation — the bot holds no master copy; its runtime artefacts are disposable.

## 6. Outcome

For this **synthetic simulation**, the residual data-protection risk is **negligible**: no
personal data exists, processing is local, the default path is offline, and no secrets are
committed. The assessment documents the controls a real deployment would need before processing
any real data, none of which is claimed here.

## Related

[`dtac-assessment.md`](dtac-assessment.md) ·
[`../clinical-safety/clinical-safety-case-report.md`](../clinical-safety/clinical-safety-case-report.md) ·
[`../clinical-safety/safety-boundary-statement.md`](../clinical-safety/safety-boundary-statement.md) ·
[`../../.env.example`](../../.env.example)
