# STAR Stories — Clinical Referral Safety Automation

> ⚠️ **Portfolio simulation — 100% synthetic data. Not a live NHS system.** OpenMRS is a mock EPR/EMR. AI assists extraction only; deterministic rules and human reviewers own every safety outcome.

Behavioural-interview answers in **Situation · Task · Action · Result** form, grounded in what was
actually built. Each story names the evidence so you can pull it up live. Tell them in the first
person; trim to ~90 seconds each.

---

## 1. Designing AI out of the safety-critical path

**Situation.** The project automates NHS referral intake, which is safety-critical: a wrong-patient
match or a missed urgent cancer referral causes real harm. Large language models are good at reading
messy referral letters but are non-deterministic and can hallucinate.

**Task.** Use AI where it genuinely helps (reading unstructured letters) without ever letting it make
a clinical decision or write an unsafe record.

**Action.** I scoped the LLM to *extraction only*, with structured output validated against a Draft-07
JSON schema, and put a deterministic regex extractor behind it as a fallback so the pipeline runs with
no key and no internet. Every *decision* is made by a separate rule engine producing reason codes; any
flag at all blocks auto-create and routes the case to a human. I made this an explicit architectural
decision and wrote it into the design and clinical-safety docs.

**Result.** Across the real run, **0 of 15 referrals were ever auto-created while carrying a safety
flag** — the core guarantee, and it's machine-checked by the acceptance gate. In interviews I frame the
restraint as the selling point: in clinical safety, "the AI only proposes" is the design, not a
weakness.

*Evidence:* `services/extraction-service/`, `services/rules-engine/`, `docs/technical/architecture.md` §4–5.

---

## 2. Testing against a spec I wrote first (oracles)

**Situation.** It's easy to build an automation that passes its own tests because the tests were
written after the code, against the code's own behaviour.

**Task.** Make the build provably correct against an independent specification, not against itself.

**Action.** Before writing any extraction or decision logic, I authored 15 *expected-outcome oracles* —
one JSON file per referral fixing the expected match result, decision, reason codes and final status,
covering all four outcome classes. Each later phase validated its real output against these oracles
(`validate_against_oracles.py`). I deliberately kept the oracles outside the input folder so the
dispatcher wouldn't ingest them, and I never edited an oracle to make a phase pass.

**Result.** **15/15 decisions match the oracle.** Because the oracles predate the implementation, a
green run is real evidence of correctness. The traceability matrix in the evidence pack maps every
referral expected-vs-actual.

*Evidence:* `data/expected-outcomes/`, `docs/testing/evidence-pack.md` §4.

---

## 3. Finding and fixing a silent duplicate-detection defect

**Situation.** A duplicate referral (same patient, same active speciality) must go to human review,
never be auto-created. REF-007 is that scenario.

**Task.** Confirm the bot actually detected the live duplicate against OpenMRS, not just against a
static fixture.

**Action.** While wiring the performer in Phase 8 I found the patient-match repository was returning
`existing_referral_status="none"` for everyone — it never queried OpenMRS for active referrals, so the
duplicate check could only ever pass by luck. I implemented a live query in
`OpenmrsPatientRepository` that reads the resolved encounter/concept UUIDs and checks for active
Referral encounters, and I added a baseline-reset script that voids and re-seeds a known
pre-existing referral so the test is reproducible.

**Result.** REF-007 now correctly resolves to **HUMAN_REVIEW** with reason codes
`MATCH_EXACT, DUPLICATE_REFERRAL`, and a reviewer rejecting it produces **no** record. The fix closed
a dependency left open since Phase 5 and is captured in the hazard log.

*Evidence:* `services/rules-engine/src/patient_repository.py`, `services/openmrs-workflow/reset_openmrs_baseline.py`, hazard log H-IDs for duplicate referral.

---

## 4. Making the human-in-the-loop real, not a Log Message

**Situation.** Many RPA "human review" steps are fake — a `Log Message` saying "would route to a
human." That proves nothing.

**Task.** Build a review loop where a clinician's decision genuinely changes the system outcome and is
fully auditable.

**Action.** I built a real SQLite review store with a lifecycle (PENDING → DECIDED → RESOLVED/FAILED),
where the row itself is the who/what/before/after/when/why audit. A clinician records APPROVE / REJECT /
AMEND with a mandatory identity and rationale (AMEND can supply missing fields). A separate resolver —
driven by a UiPath process — re-reads those decisions: approved/amended referrals are written to
OpenMRS and verified; rejected ones get no record. It's idempotent and appends a resolution row to the
audit log per outcome.

**Result.** Of 10 reviewed referrals, **6 were approved or amended into OpenMRS and 4 were rejected**.
A degraded-fax case (REF-013) was *amended* to supply the specialty and reason a human read off the
scan that the extractor couldn't. The human decision demonstrably changes the final state.

*Evidence:* `services/review-service/`, `uipath/NHS.ReferralSafety.ReviewResolver/`, `docs/testing/phase9-acceptance.md`.

---

## 5. Separating business from system exceptions (REFramework discipline)

**Situation.** REF-014 is not actually a referral; REF-015 is a corrupt file. Treating both the same way
would be wrong — one should never be retried, the other should.

**Task.** Handle the two exception classes per REFramework convention so retries and escalation behave
correctly.

**Action.** I mapped *not-a-referral* to a **BusinessRuleException** (no retry, move to `failed/`) and
*corrupt/unreadable* plus any transient service or OpenMRS failure to a **system Exception** (retry,
screenshot, escalate). I set `MaxRetryNumber` and `MaxConsecutiveSystemExceptions` deliberately and
documented the policy in the design spec. Crucially I classified human review as a *success* outcome,
not an exception, so the metrics stay honest.

**Result.** The live run produced exactly **1 business exception and 1 system exception**, handled
distinctly, with the queue item dispositions correct. This is a standard senior-RPA interview question
and I can walk the state machine end to end.

*Evidence:* `uipath/NHS.ReferralSafety.Performer/Framework/Process.xaml`, `uipath/design/reframework-design-spec.md`, `docs/testing/phase7-acceptance.md`.

---

## 6. Generated, drift-proof evidence (no hand-typed numbers)

**Situation.** Portfolio projects often claim results in a README that no longer match the code. A
reviewer can't trust them.

**Task.** Make every reported figure trace back to an artifact, and make the docs impossible to silently
drift.

**Action.** I built a reporting layer with a single source of truth (`report_model.py`) that folds the
decision artifacts, the review store, the audit log and the oracles into one model — then *generates*
the Excel workbook, the HTML dashboard and the markdown evidence pack from it. The Phase 12 acceptance
gate re-derives the entire pack and **compares it to the committed file**, failing if they differ. I
also wrote a clinical-safety pack validator that checks every hazard's control-evidence path actually
resolves to a real file.

**Result.** Every headline number — 15 tested, 15/15 vs oracle, 9 created, 0 unsafe — is generated and
machine-checked. Eleven prior acceptance gates plus the Phase 12 consolidation all pass. The docs can't
lie because a test fails if they do.

*Evidence:* `services/reporting/`, `services/testing/`, `docs/clinical-safety/validate_pack.py`.

---

## 7. Building under hard constraints (synthetic data, idempotency, no filler)

**Situation.** I set strict rules up front: synthetic data only, every core action must hit a real
system (no `Log Message` filler), idempotent re-runs, everything auditable.

**Task.** Hold to those constraints across a 13-phase build without cutting corners under time pressure.

**Action.** I used the reserved 999-range for synthetic NHS numbers with valid Modulus-11 check digits,
tagged every record `SYNTHETIC`, kept secrets out of the repo behind `.env.example`, and gated each
phase on its own acceptance test before starting the next. Idempotency is keyed on the referral
reference so re-running never double-writes to OpenMRS.

**Result.** Thirteen phases, each with a committed acceptance record and a clean git history of one
commit per phase. The discipline is the point: it's what makes the project defensible in an NHS
interview rather than just a demo.

*Evidence:* `docs/business/project-scope.md` (DoD), `docs/testing/phase1-acceptance.md` … `phase13-acceptance.md`, git history.

---

## How to use these

- **"Tell me about a project you're proud of."** → Story 1 + the headline numbers.
- **"How do you ensure quality / how do you test?"** → Stories 2 and 6.
- **"Tell me about a bug you found / a time you dug into a problem."** → Story 3.
- **"How would you use AI safely in healthcare?"** → Story 1.
- **"Explain REFramework / exception handling."** → Story 5.
- **"A time you worked to a tight standard / constraint."** → Story 7.
