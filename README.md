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

## Results at a glance

From the real end-to-end run (generated, not hand-typed — see
[`docs/testing/evidence-pack.md`](docs/testing/evidence-pack.md)):

| Metric | Value |
|---|---|
| Synthetic referrals processed end-to-end | **15** |
| Decisions matching the independently-written oracle | **15/15** |
| Created in OpenMRS | **9** (3 automated + 6 human-approved/amended) |
| Routed to human review | **10 (67%)** |
| Rejected at review (no record) | **4** |
| Exceptions (business + system), handled distinctly | **2** |
| **Auto-created while carrying a safety flag** | **0** — the core safety guarantee |
| Append-only audit rows (who/what/before/after/when/why) | **25** |
| Named clinical-safety hazards mapped to real controls | **12** |

> **The principle throughout: AI proposes, deterministic rules and human reviewers decide.**

📊 Portfolio dashboard: [`reports/dashboard.html`](reports/dashboard.html) (self-contained, open in a browser).
💼 Interview pack (CV bullets · STAR stories · demo script · Q&A): [`docs/cv-linkedin/`](docs/cv-linkedin/).

## Quick start

```bash
# 1. Start OpenMRS (mock EPR) — ready when REST /ws/rest/v1/session returns authenticated:true
docker compose -f openmrs-setup/docker-compose.yml up -d

# 2. (offline, no UiPath needed) reproduce the decision pipeline against the oracles
cd services/extraction-service && python run_extraction.py && python validate_against_oracles.py   # 15/15
cd ../rules-engine          && python run_decisions.py   && python validate_against_oracles.py      # 15/15

# 3. Regenerate the evidence and confirm every gate
python services/reporting/build_all.py            # Excel workbook + dashboard.html
python services/testing/build_evidence_pack.py    # docs/testing/evidence-pack.md
python services/testing/validate_acceptance.py    # Phase 12 gate → 8/8
python docs/clinical-safety/validate_pack.py      # safety pack gate → 9/9
python docs/cv-linkedin/validate_pack.py          # Phase 13 packaging gate → 5/5
```

The full live UiPath run (Orchestrator queue + REFramework Performer + human-review resolver) is
documented in [`docs/testing/phase8-acceptance.md`](docs/testing/phase8-acceptance.md) and
[`docs/testing/phase9-acceptance.md`](docs/testing/phase9-acceptance.md). Requires `uip login`, the
`.NET` toolchain, and the three Python services running. Python 3.9+; stdlib only except `openpyxl`
(reporting) and an optional LLM key.

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
| 5 — Rules & safety decision engine | ✅ complete (patient match + deterministic safety rules; 15/15 decisions match oracles; risky→review) |
| 6 — OpenMRS workflow mapping | ✅ complete (REST create + re-read verify; idempotent; live duplicate check; 11/11 acceptance) |
| 7 — REFramework design spec | ✅ complete (buildable Dispatcher + Performer design, Config.xlsx, BE/SE separated; 12/12 design review) |
| 8 — UiPath build | ✅ complete (Dispatcher + REFramework Performer; live Orchestrator queue run; 15/15 — 3→OpenMRS, 10→review, dup detected, 1 BE, 1 SE) |
| 9 — Human-in-the-loop review | ✅ complete (real SQLite store; clinician APPROVE/REJECT/AMEND; UiPath ReviewResolver applied 6→OpenMRS, 4→no record; audited, idempotent; 8/8) |
| 10 — Reporting + dashboard | ✅ complete (Excel workbook + self-contained HTML dashboard from the real run; 9 created/4 rejected/2 exceptions, 0 unsafe auto-creates; reconciles with audit + oracles; 8/8) |
| 11 — Clinical safety + governance docs | ✅ complete (DCB0129/0160/DTAC/DPIA-inspired pack; 12 named hazards mapped to real controls; machine-checked 9/9) |
| 12 — Testing + evidence pack | ✅ complete (generated evidence pack + test plan; all 15 scenarios across 4 outcome classes, 15/15 vs oracles, 11/11 prior gates; machine-checked 8/8) |
| 13 — GitHub/CV/LinkedIn packaging | ✅ complete (interview-ready README, demo script, STAR stories, CV/LinkedIn bullets, interview Q&A; machine-checked 5/5) |

**All 13 phases complete.** Every phase passed its own acceptance gate before the next began.

## Key documents

- Architecture — [`docs/technical/architecture.md`](docs/technical/architecture.md)
- Project scope & DoD — [`docs/business/project-scope.md`](docs/business/project-scope.md)
- Clinical safety pack (DCB0129-inspired) — [`docs/clinical-safety/`](docs/clinical-safety/) (safety boundary, risk-management plan, hazard log, safety case)
- Information governance (DPIA + DTAC) — [`docs/information-governance/`](docs/information-governance/)
- Test plan & consolidated evidence pack — [`docs/testing/test-plan.md`](docs/testing/test-plan.md) · [`docs/testing/evidence-pack.md`](docs/testing/evidence-pack.md)
- Interview / CV / LinkedIn pack — [`docs/cv-linkedin/`](docs/cv-linkedin/) (demo script, STAR stories, interview Q&A, copy-paste CV & LinkedIn bullets)

## Safety & data

100% synthetic data. Synthetic NHS-style numbers use the reserved 999-test range and are
tagged `SYNTHETIC`. No secrets in the repo — see [`.env.example`](.env.example).
