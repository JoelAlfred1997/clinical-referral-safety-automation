# CV & LinkedIn Assets — Clinical Referral Safety Automation

> ⚠️ **Portfolio simulation — 100% synthetic data. Not a live NHS system.** OpenMRS is a mock EPR/EMR. AI assists extraction only; deterministic rules and human reviewers own every safety outcome.

Copy-paste blocks for a CV, a LinkedIn "Featured" project, an About section, and a launch post.
Pick the length that fits; all figures are from the real run (see
[`docs/testing/evidence-pack.md`](../testing/evidence-pack.md)).

---

## 1. CV — project entry (full)

**Clinical Referral Safety Automation** — *UiPath REFramework · OpenMRS · AI-assisted extraction · Clinical-safety controls*
*Self-directed portfolio build (synthetic data; OpenMRS as a mock EPR)*

- Built an end-to-end UiPath REFramework solution that ingests synthetic NHS referral letters via an
  Orchestrator queue, extracts them, validates patients against a real EMR (OpenMRS) over REST, and
  applies clinical-safety, patient-match and duplicate-detection rules.
- Scoped AI to **extraction only** (LLM with structured output + JSON-schema validation, behind a
  deterministic regex fallback); all decisions are made by a rule engine producing reason codes —
  **0 of 15 referrals were ever auto-created while carrying a safety flag.**
- Processed all **15** scenario referrals end-to-end with decisions matching an independently-authored
  oracle **15/15**: 9 created in OpenMRS (3 automated + 6 human-approved), 10 routed to human review
  (67%), and business vs system exceptions handled distinctly per REFramework.
- Implemented a **real human-in-the-loop review store** (SQLite) where a clinician's APPROVE/REJECT/
  AMEND decision — with identity and rationale — changes the final outcome and is fully audited.
- Wrote a **DCB0129/DCB0160/DTAC/DPIA-inspired clinical-safety pack** (12 named hazards mapped to real
  controls on a 5×5 risk matrix) and a generated, **machine-checked evidence pack** so reported
  results can't drift from the code.

## 2. CV — project entry (compact, 3 bullets)

**Clinical Referral Safety Automation** — *UiPath REFramework · OpenMRS · AI-assisted extraction*

- End-to-end RPA bot for NHS referral intake: Orchestrator queue → AI-assisted extraction (LLM + regex
  fallback, schema-validated) → patient match & clinical-safety rules → REST writes to a real EMR
  (OpenMRS), with append-only audit logging.
- Safety by design: AI proposes, deterministic rules and a real human-review loop decide; **0/15**
  unsafe auto-creates, **15/15** decisions matching an independent oracle, 67% routed to human review.
- Includes a DCB0129/0160-inspired clinical-safety pack (12 named hazards → real controls) and a
  generated, machine-checked evidence pack across 11+ phase acceptance gates.

## 3. CV — one-liner (for a skills/projects strip)

> *Clinical Referral Safety Automation* — UiPath REFramework bot automating NHS referral intake against
> a real EMR (OpenMRS) with AI-assisted extraction, clinical-safety rules, a human-review loop, full
> audit, and DCB0129-inspired governance. Synthetic data; 15/15 vs oracle; 0 unsafe auto-creates.

---

## 4. LinkedIn — "About"/Featured blurb

> I built an end-to-end Intelligent Automation project to NHS standards: a UiPath REFramework bot that
> safely automates clinical referral intake.
>
> A synthetic referral letter arrives, the bot extracts it (LLM with a deterministic fallback),
> validates the patient against a real EMR (OpenMRS), runs duplicate and clinical-safety checks, and
> then either creates the record, routes it to a real human-review queue, or raises an exception — every
> step audited.
>
> The design choice I care about most: the AI only *proposes*. Deterministic rules and human reviewers
> own every safety outcome. Across the run, zero referrals were auto-created while carrying a safety
> flag, and every decision matched a spec I wrote before the code.
>
> It ships with a DCB0129/0160/DTAC-inspired clinical-safety pack — 12 named hazards mapped to real
> controls — and a generated, machine-checked evidence pack. 100% synthetic data.

## 5. LinkedIn — launch post

> 🏥 New portfolio project: **Clinical Referral Safety Automation** (UiPath + OpenMRS)
>
> NHS referral intake is high-volume and safety-critical — wrong-patient matches, duplicates, and
> missed urgent cancer referrals cause real harm. So I built a REFramework bot that automates the
> *safe* parts and routes everything risky to a human.
>
> How it works:
> 📥 Orchestrator queue ingests synthetic referral letters
> 🤖 AI-assisted extraction (LLM + regex fallback, schema-validated)
> 🔎 Patient match + duplicate + clinical-safety rules against a real EMR (OpenMRS over REST)
> 👩‍⚕️ Real human-in-the-loop review — a clinician's decision changes the outcome
> 🧾 Append-only audit trail + generated dashboard/report
> 🛡️ DCB0129/0160/DTAC-inspired safety pack: 12 named hazards → real controls
>
> The principle throughout: **AI proposes, rules and humans decide.** Across the run — 15/15 decisions
> matched the spec I wrote first, and 0 referrals were ever auto-created while carrying a safety flag.
>
> Built phase by phase, each gated by an acceptance test, all on 100% synthetic data (OpenMRS as a mock
> EPR — not a live NHS system).
>
> #UiPath #RPA #IntelligentAutomation #NHS #HealthTech #ClinicalSafety #AI

---

## 6. Skills / keywords (for CV skills section & LinkedIn skills)

UiPath · REFramework · Orchestrator (queues, assets, credentials) · RPA · Intelligent Automation ·
Dispatcher/Performer pattern · business vs system exception handling · idempotent design ·
AI-assisted extraction (LLM) · structured output / JSON-schema validation · prompt-to-fallback design ·
REST API automation · OpenMRS / EMR data model · patient matching · duplicate detection ·
clinical-safety rules · human-in-the-loop · append-only audit logging · SQLite · Python ·
DCB0129 / DCB0160 / DTAC / DPIA · test oracles & acceptance gates · reporting & dashboards · Docker · Git

---

## 7. Elevator pitch (spoken, ~20s)

> "I built a UiPath bot that automates NHS referral intake against a real EMR. It reads the referral
> with AI, matches the patient, runs clinical-safety and duplicate checks, then creates the record or
> sends it to a human — all audited. The whole design keeps AI out of the decision: it proposes, rules
> and people decide. Zero unsafe auto-creates across the run, all on synthetic data."

---

## Tips

- Keep the **synthetic-data / not-a-live-NHS-system** caveat visible. It signals you understand IG and
  clinical-safety boundaries — a plus, not a hedge.
- Lead with the **safety guarantee** (0 unsafe auto-creates) and the **oracle result** (15/15); they're
  the most credible, specific claims.
- Link the repo and the [dashboard](../../reports/dashboard.html) / [evidence pack](../testing/evidence-pack.md) so reviewers can verify.
- Pair these bullets with the [STAR stories](star-stories.md) for the interview itself.
