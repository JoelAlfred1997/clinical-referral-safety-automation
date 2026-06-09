# Architecture — Clinical Referral Safety Automation

> Portfolio simulation. Synthetic data only. OpenMRS is a **mock** EPR/EMR.
> AI assists; it does **not** make clinical decisions. Status: **Phase 0 (design)**.

---

## 1. System context (C4 level 1)

```
                          ┌──────────────────────────────────────┐
   Synthetic referral     │          UiPath Robot                │
   PDFs / TXT  ─────────▶ │   NHS.ReferralSafety.Automation       │
   (data/input-referrals) │   (REFramework, attended/unattended)  │
                          └───────┬───────────────┬───────────────┘
                                  │               │
        ┌─────────────────────────┘               └─────────────────────────┐
        ▼                                                                     ▼
┌─────────────────┐   HTTP/REST    ┌──────────────────┐         Browser UI  ┌──────────────────┐
│ Extraction svc  │◀──────────────│  Orchestrator     │                     │   OpenMRS         │
│ (Python/Flask)  │   queue items  │  Queue + Assets   │   REST + UI autom.  │  (Docker, local)  │
│ LLM + regex     │                └──────────────────┘ ───────────────────▶│  mock EPR/EMR     │
└─────────────────┘                                                          └──────────────────┘
        │                                                                              │
        ▼                                                                              ▼
┌─────────────────┐                ┌──────────────────┐                     ┌──────────────────┐
│ extracted-json  │                │ Audit DB (SQLite)│                     │ Review store      │
│ (per referral)  │                │ append-only      │                     │ (SQLite/Excel)    │
└─────────────────┘                └──────────────────┘                     │ human-in-the-loop │
        │                                   │                               └──────────────────┘
        └────────────────┬──────────────────┘                                        │
                         ▼                                                            ▼
                ┌──────────────────┐                                       ┌──────────────────┐
                │ Excel report +   │                                       │ Reviewer decision│
                │ optional dashboard│                                      │ feeds back to bot│
                └──────────────────┘                                       └──────────────────┘
```

## 2. End-to-end data flow (one transaction = one referral)

1. **Dispatcher** scans `data/input-referrals/`, creates one Orchestrator **Queue item** per file.
2. **Performer** (REFramework) gets a queue item.
3. Extract raw text from the referral file (PDF → text, or read TXT).
4. Call the **extraction service** (LLM with structured output) → JSON. If `USE_LLM=false` or the call fails → **deterministic regex** fallback.
5. **Validate JSON** against schema; compute `missing_fields` and `confidence_score`.
6. **Search patient in OpenMRS** (REST query by identifier, then demographics).
7. **Validate patient match** (exact / DOB-mismatch / partial / multiple / none).
8. **Check duplicate referral** (same patient + speciality + active encounter within lookback window).
9. **Apply clinical safety rules** → produce a single `DecisionOutcome` + reason codes.
10. Branch:
    - `AUTO_CREATE_REFERRAL_RECORD` → create Referral encounter/observations in OpenMRS (REST), verify by re-read.
    - `HUMAN_REVIEW_REQUIRED` → create a real review record (SQLite/Excel/Action Center).
    - `BUSINESS_EXCEPTION` → log reason, move file to `failed/`.
    - `SYSTEM_EXCEPTION` → retry per REFramework, screenshot, escalate.
11. **Write audit log** (before/after values, decision reason, identity, timestamp).
12. **Move source file** to `processed/`, `failed/`, or `review/`.
13. **Update Excel report**; continue to next transaction.

## 3. Component responsibilities

| Component | Tech | Responsibility | Why it is "real" (not filler) |
|---|---|---|---|
| Dispatcher | UiPath | Enumerate inputs, push queue items | Real Orchestrator queue items |
| Performer | UiPath REFramework | Per-referral processing | Real workflow with TX state machine |
| Extraction service | Python (Flask) + LLM/regex | Text → structured JSON | Real HTTP service, real JSON artefacts |
| OpenMRS | Docker | Mock EPR: patients, encounters, obs | Real REST writes + UI, verifiable |
| Audit DB | SQLite | Append-only audit trail | Real DB rows, queryable evidence |
| Review store | SQLite / Excel / Action Center | Human-in-the-loop | Real records a human updates |
| Reporting | Excel + optional Streamlit | Run evidence + metrics | Real data from processed runs |

## 4. Key design decisions (and the trade-offs)

- **OpenMRS replaces a hand-built mock PAS/EPR.** Saves weeks, demonstrably "real" clinical system, has a REST API and FHIR. Cost: setup weight (Docker) and a learning curve on its data model.
- **REST-first, UI for evidence.** OpenMRS 3.x (O3) front end is a React SPA — fragile for selector-based UI automation. We do **record creation via REST** for reliability, and use **UI automation for patient search/confirm** (the screenshot-worthy, demo-able part). If UI selectors prove unstable, fall back to the **legacy Reference Application 2.x UI**, which is friendlier to UiPath. This is documented per Phase 6.
- **"Agentic AI" is scoped deliberately narrow.** The LLM does extraction + suggested classification with **structured output and schema validation**, behind a deterministic fallback. We do **not** let an autonomous agent loop drive clinical writes. In a clinical-safety context, that restraint is the selling point, not a weakness — say so in interviews.
- **Synthetic NHS numbers use the reserved 999-test range** with a valid Modulus-11 check digit, and every record is tagged `SYNTHETIC`. See `docs/information-governance/`.
- **Human review is a real store**, not a `Log Message`. Default SQLite review table; Action Center optional if Orchestrator supports it.

## 5. What controls safety

Rule-based checks and human review own every safety-sensitive outcome. The LLM can only *propose*. Any uncertain, urgent, incomplete, duplicate, or patient-match-risk case is routed to a human. Every decision carries a reason code and an audit row. See `docs/clinical-safety/`.
