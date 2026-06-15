# Interview Q&A — Clinical Referral Safety Automation

> ⚠️ **Portfolio simulation — 100% synthetic data. Not a live NHS system.** OpenMRS is a mock EPR/EMR. AI assists extraction only; deterministic rules and human reviewers own every safety outcome.

Likely questions for an NHS RPA / Intelligent Automation interview, with grounded answers and the file
to open if they want proof. Pair with the [STAR stories](star-stories.md) for behavioural prompts.

---

## Architecture & RPA

**Q. Walk me through the architecture.**
One referral is one transaction. A **Dispatcher** scans `data/input-referrals/` and creates one
Orchestrator queue item per file (unique reference). A **REFramework Performer** takes each item,
extracts the letter (LLM with regex fallback), validates the patient against OpenMRS over REST, runs
duplicate and clinical-safety rules, then branches: auto-create, human review, business exception, or
system exception. Every step writes an audit row. *Open:* `docs/technical/architecture.md`.

**Q. Why the Dispatcher/Performer split?**
Separation of concerns and resilience. The Dispatcher just enqueues work fast; the Performer processes
transactionally with REFramework's state machine, retries and per-item exception handling. If the
Performer dies mid-run, the queue preserves state — work isn't lost or double-done.

**Q. How do you handle exceptions?**
Business vs system, deliberately. *Not-a-referral* (REF-014) is a **BusinessRuleException** — no retry,
move to `failed/`. *Corrupt file* (REF-015) and any transient service/OpenMRS failure is a **system
Exception** — retry, screenshot, escalate. Human review is a *success* outcome, not an exception, so
metrics stay honest. `MaxRetryNumber` and `MaxConsecutiveSystemExceptions` are set intentionally.
*Open:* `uipath/NHS.ReferralSafety.Performer/Framework/Process.xaml`.

**Q. Is it idempotent? What happens on a re-run?**
Yes. Writes to OpenMRS are keyed on the referral reference (REF-NNN), so re-running never creates a
duplicate record. The review resolver skips already-RESOLVED rows. I demo this by running twice and
showing nothing changes the second time.

**Q. How is it configured?**
Config-driven via the REFramework `Config.xlsx` — queue name, folder, service URLs, data paths in
Settings/Constants/Assets. Credentials come from Orchestrator assets, not the workflow. The LLM key
lives in a service `.env`, never in a UiPath asset or the repo.

---

## AI & safety

**Q. Where exactly does AI sit, and why so narrow?**
The LLM does **extraction only** — turning an unstructured letter into structured JSON — with structured
output validated against a Draft-07 schema. A deterministic regex extractor sits behind it so the
pipeline runs with no key and no internet. Every *decision* is a separate rule engine. In clinical
safety, keeping a non-deterministic model out of the decision path is the design, not a limitation.

**Q. What if the LLM hallucinates or returns garbage?**
Three guards: schema validation rejects malformed output; the regex fallback covers failures and the
no-key case; and low extraction confidence is itself a reason code that routes the case to a human
(e.g. REF-013, the degraded scan). The model can never push an unverified field into a created record.

**Q. How do you *prove* AI never made an unsafe decision?**
The rule engine flags any concern, and **any flag blocks auto-create**. The acceptance gate asserts the
invariant directly: across the run, **0 of 15** referrals were auto-created while carrying a safety
flag. *Open:* `docs/testing/evidence-pack.md` §2.

**Q. What clinical-safety scenarios did you cover?**
DOB mismatch, partial and multiple patient matches, duplicate referral, urgent 2-week-wait suspected
cancer, safeguarding child, no-match, incomplete mandatory fields, and low extraction confidence — plus
clean auto-creates, a not-a-referral, and a corrupt file. 15 scenarios, four outcome classes.

---

## Quality & testing

**Q. How do you know it's correct?**
I wrote 15 **expected-outcome oracles before** the implementation — independent spec files fixing the
expected match, decision, reason codes and status. Each phase validates real output against them. Result
is **15/15**, and because the oracles predate the code, that's genuine evidence, not circular. *Open:*
`data/expected-outcomes/` and `docs/testing/evidence-pack.md` §4.

**Q. How do you stop the README/results drifting from the code?**
Everything is generated. The reporting layer folds the artifacts into one model and generates the Excel
workbook, the dashboard and the markdown evidence pack. The Phase 12 gate re-derives the pack and
compares it to the committed file — the test fails if they differ. No figure is hand-typed.

**Q. What does "real" mean here vs filler?**
No `Log Message` standing in for an action. Referrals are created as actual encounters/observations in
OpenMRS over REST and verified by re-read; review is a real SQLite store a human updates; audit is real
append-only rows. *Open:* OpenMRS SPA + `data/audit/audit-log.csv`.

---

## Data, governance & IG

**Q. How is patient data handled?**
100% synthetic. Synthetic NHS numbers use the reserved 999-test range with a valid Modulus-11 check
digit, and every record is tagged `SYNTHETIC`. No real or production NHS system, network, or data is
touched. *Open:* `docs/information-governance/`.

**Q. You mention DCB0129/0160 — what did you actually produce?**
A clinical-risk-management plan, a hazard log of 12 named hazards (each with causes, clinical effect,
existing controls, control *evidence pointing at real files*, and initial/residual risk on a 5×5
matrix), and a clinical-safety case report. It's DCB-*inspired* — a simulation, not formal
certification — and a validator checks every control-evidence path resolves. *Open:*
`docs/clinical-safety/hazard-log.csv`.

**Q. What's the one residual risk you couldn't fully control?**
The human review-queue backlog (operational, DCB0160-flavoured) — if reviewers don't work the queue,
urgent referrals wait. That's owned by the deploying organisation, not the bot, and it's logged as the
only residual High. Naming it honestly is the point.

---

## Reflection

**Q. What would you do differently / what's next?**
Production would need real NHS auth (CIS2/Smartcard), e-RS/PDS integration, infosec hardening, and
formal clinical-safety assurance with a qualified Clinical Safety Officer — all explicitly out of scope
here. Technically I'd add Action Center for review instead of SQLite, and a proper queue-backed retry
for the services.

**Q. What was the hardest part?**
Making the duplicate check real. The patient repository was silently returning "no existing referral"
for everyone, so the duplicate scenario passed by luck. I implemented a live OpenMRS query plus a
reproducible baseline-reset, which closed a dependency open since Phase 5. *Open:*
`services/rules-engine/src/patient_repository.py`.

**Q. Why OpenMRS instead of building a mock EPR?**
A real EMR with a REST API and a documented data model is far more credible than a hand-faked store, and
it forced me to deal with a genuine clinical data model (encounters, observations, concepts). The
trade-off was Docker setup weight and a learning curve on its data model.

**Q. How did you keep a 13-phase build on track solo?**
One phase at a time, each with its own acceptance test that had to pass before the next started, a
committed acceptance record per phase, one git commit per phase, and a running Word build log so I could
resume cold. The discipline is what makes it defensible rather than just a demo.
