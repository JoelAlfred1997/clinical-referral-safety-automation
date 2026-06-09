# Project Scope — Clinical Referral Safety Automation

**Full title:** Clinical Referral Safety Automation using UiPath REFramework, OpenMRS EMR, Synthetic Patient Data, Agentic AI and Clinical Safety Controls

**Status:** Portfolio simulation — not a live NHS deployment.
**Data:** 100% synthetic. No real patient data is permitted at any point.

---

## 1. Problem statement

NHS referral intake is high-volume, error-prone, and safety-critical. Wrong-patient
matching, duplicate referrals, and delayed urgent (e.g. 2-week-wait suspected cancer)
referrals cause real harm. This project automates the *safe, deterministic* parts of
referral intake while routing every risky or ambiguous case to a human — and proves it
with auditable evidence.

## 2. Goal

A fully end-to-end RPA solution, showcasable on CV / GitHub / LinkedIn and defensible in
NHS RPA / Intelligent Automation interviews, that demonstrates REFramework, Orchestrator
queues, config-driven design, AI-assisted extraction with deterministic guardrails,
patient matching, duplicate detection, clinical-safety decisioning, human-in-the-loop
review, audit logging, and clinical-safety governance documentation (DCB0129/DCB0160/DTAC-inspired).

## 3. In scope

- Ingesting synthetic referral PDFs/TXT via an Orchestrator queue.
- LLM-assisted + regex-fallback extraction to a validated JSON schema.
- Patient search and match validation against OpenMRS (mock EPR).
- Referral completeness, duplicate-referral, and clinical-safety rule checks.
- Creating/updating referral-style records in OpenMRS via REST (+ UI for evidence).
- Real human-in-the-loop review store with feedback into final status.
- Append-only audit logging and Excel/dashboard reporting.
- Clinical-safety and IG documentation pack.

## 4. Out of scope (explicitly)

- Any real or production NHS system, data, or network (NHS Spine, PDS, e-RS, real PAS/EPR).
- Real patient-identifiable data of any kind.
- Autonomous AI making final clinical or referral-acceptance decisions.
- Clinical triage prioritisation as a medical decision (the bot routes, clinicians decide).
- Production-grade infosec hardening, HA/DR, or formal clinical-safety certification.
- Integration with real NHS authentication (Smartcard/CIS2).

## 5. What this project IS vs IS NOT

| IS | IS NOT |
|---|---|
| A realistic, end-to-end RPA portfolio build | A live or pilot NHS system |
| Genuine interaction with a real EMR (OpenMRS) | A custom hand-faked EPR with `Log Message` filler |
| AI-*assisted* extraction with human control | AI-*driven* clinical decision-making |
| Synthetic data, clearly labelled | Anything touching real patient data |
| DCB0129/0160/DTAC-*inspired* safety thinking | Formally assured/certified clinical software |

## 6. Definition of Done (whole project)

The project is "done" when **all 15 synthetic referral scenarios** run end-to-end and:

1. Each referral produces validated extraction JSON saved for audit.
2. Patient match status is computed correctly for exact/partial/duplicate/no-match cases.
3. Clean, complete, unambiguous referrals are **created in OpenMRS** and verified by re-read.
4. Every risky/incomplete/urgent/ambiguous/duplicate case is routed to **human review** with a reason code.
5. A human review decision can be recorded and **changes the final outcome**.
6. Every system action writes an **audit row** (who/what/before/after/when/why).
7. Business vs system exceptions are distinct and handled per REFramework.
8. The bot is **idempotent / safely re-runnable** (no duplicate OpenMRS records on rerun).
9. Excel report + optional dashboard reflect the real run.
10. Clinical-safety + IG docs exist and are specific (named hazards, named controls).
11. README, demo script, and CV/LinkedIn assets are interview-ready.
12. No secrets in the repo; `.env.example` present; synthetic-data notice everywhere.

## 7. Phase roadmap

| Phase | Deliverable | Acceptance gate |
|---|---|---|
| 0 | Scope + architecture (this) | Architecture realistic; OpenMRS replaces mock EPR; no filler |
| 1 | OpenMRS running locally | Login + patient search work; update path identified |
| 2 | ≥30 synthetic patients in OpenMRS | Search returns them; match/partial/dup/no-match cases exist |
| 3 | ≥15 synthetic referrals + expected-outcome files | All scenarios + expected outcomes exist |
| 4 | Extraction service (LLM + regex + validation) | Each referral → valid JSON; flags + confidence correct |
| 5 | Rules & safety decision engine | Every decision has a reason code; risky → review |
| 6 | OpenMRS workflow mapping | Concrete, executable update path; no log-message-only steps |
| 7 | REFramework design spec | Buildable from the spec; BE/SE separated |
| 8 | UiPath build | Processes all 15; clean→OpenMRS, risky→review, dup detected |
| 9 | Human-in-the-loop review | Real store; decisions affect outcome; auditable |
| 10 | Reporting + dashboard | Real data; portfolio screenshots |
| 11 | Clinical safety + governance docs | Specific, professional, clearly a simulation |
| 12 | Testing + evidence pack | All 15 tested; happy/BE/SE/review demonstrated |
| 13 | GitHub/CV/LinkedIn packaging | README, demo, STAR, bullets ready |

**Rule:** no phase advances until its acceptance test passes.
