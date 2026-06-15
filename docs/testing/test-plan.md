# Test Plan — Clinical Referral Safety Automation

> ⚠️ **Portfolio simulation — 100% synthetic data. Not a live NHS system.**
> OpenMRS is a mock EPR/EMR. AI assists extraction only; deterministic rules and human
> reviewers own every safety outcome.

This is the master test plan for the project. It defines *how* the solution is tested,
*what* must pass for it to be considered done, and *where* the evidence lives. The
generated [evidence pack](evidence-pack.md) is the consolidated result; the per-phase
`phaseN-acceptance.md` records are the detailed evidence for each component.

---

## 1. Objectives

Prove that the automation:

1. processes **all 15 synthetic referral scenarios** end-to-end, and
2. produces the **correct, safe outcome** for each — measured against an independent test
   oracle defined *before* the bot was built (Phase 3), and
3. **never makes a risky clinical call on its own** — every uncertain, urgent, incomplete,
   duplicate or patient-match-risk case is routed to a human, and
4. is **auditable and idempotent** — every action leaves an audit row and reruns create no
   duplicate records.

These map directly to the project Definition of Done (`docs/business/project-scope.md` §6).

## 2. Test approach

The project is tested at four levels; Phase 12 consolidates them.

| Level | What | Where |
|---|---|---|
| **Component / oracle tests** | Each service (extraction, rules, OpenMRS workflow, review, reporting) re-derives its output from inputs and compares against the Phase 3 oracles. | `services/*/validate_*.py`, recorded in `phase4..11-acceptance.md` |
| **Integration (live)** | The UiPath REFramework bot runs against a real Orchestrator queue + live OpenMRS, exercising the real HTTP services. | `phase8-acceptance.md` |
| **Human-in-the-loop** | A real review store; clinician decisions (APPROVE / REJECT / AMEND) are recorded and the bot resolves them, changing the final outcome. | `phase9-acceptance.md` |
| **System / acceptance (this plan)** | All 15 scenarios across the four outcome classes, reconciled with the audit log, with the safety invariant enforced. | `evidence-pack.md`, `services/testing/validate_acceptance.py` |

**Oracle-driven, not assertion-by-eye.** The expected result for every referral is fixed
in `data/expected-outcomes/REF-NNN.expected.json`. Tests compare the bot's *actual*
artifacts against these oracles. Numbers in the evidence pack are **generated** from the
artifacts — none are hand-typed — so the documentation cannot silently drift from reality.

## 3. The four outcome classes

Every referral resolves into exactly one class. The plan requires each to be demonstrated.

| Class | Meaning | REFramework handling | Scenarios |
|---|---|---|---|
| **Happy path (straight-through)** | Clean, complete, exact-match, no safety flag → auto-created in OpenMRS. | Queue item *Successful* | REF-001, 002, 003 |
| **Human review** | Any patient-match risk, duplicate, urgent/2WW, safeguarding, incomplete, low-confidence, or no-match → routed to a human with a reason code. A *successful* business outcome, not an exception. | Queue item *Successful*; row written to review store | REF-004 … 013 |
| **Business exception** | The input is not a valid referral (no clinical retry will help). | `BusinessRuleException`, no retry | REF-014 |
| **System exception** | The input is unreadable / a transient technical failure. | `Exception`, retry → escalate | REF-015 |

## 4. Scenario coverage

15 scenarios cover every match result, every safety-routing reason, and both exception
types. The full expected/actual matrix is in [evidence-pack.md §4](evidence-pack.md); the
scenario design rationale is in `data/expected-outcomes/README.md`.

- **Match results:** exact · DOB-mismatch · partial · multiple-candidate · no-match · not-applicable.
- **Safety routing reasons:** wrong-patient risk · duplicate · urgent/2WW cancer ·
  safeguarding/child · incomplete · low extraction confidence · not-a-referral · unreadable file.
- **Bot decisions:** AUTO_CREATE ×3 · HUMAN_REVIEW ×10 · BUSINESS_EXCEPTION ×1 · SYSTEM_EXCEPTION ×1.

## 5. Test environment

- OpenMRS 3 reference app via Docker (`openmrs-setup/docker-compose.yml`), seeded with 32
  synthetic patients (999-range NHS numbers) + Reed's pre-existing Cardiology referral.
- Three stdlib HTTP services: extraction `:8089`, decision `:8090`, writeback `:8091`;
  review service `:8092` (Phase 9).
- UiPath Studio/Robot with the `NHS_Referrals` Orchestrator queue (folder *Shared*,
  unique reference). See `docs/testing/phase8-acceptance.md` for the toolchain setup.
- Python 3 (stdlib + `openpyxl` for the Phase 10 workbook).

## 6. Entry / exit criteria

**Entry:** Phases 1–11 complete and PASS; a Phase 8 + Phase 9 run present in `data/`.

**Exit (Phase 12 PASS):** `python services/testing/validate_acceptance.py` reports **8/8**:

1. all 15 referrals present and tested,
2. every decision matches its Phase 3 oracle (15/15),
3. all four outcome classes demonstrated with the expected counts (3/10/1/1),
4. human review changes the outcome in both directions (approved-in and rejected-out),
5. safety invariant — **0** referrals auto-created while carrying a safety flag,
6. every referral appears in the append-only audit log,
7. every prior phase acceptance record (phase1..11) is PASS,
8. the generated evidence pack is present, banner-carrying, and matches the model.

## 7. Risks & limitations of the test

- Synthetic data only; no NHS Spine/PDS/e-RS, no real authentication. The scope boundary is
  in `docs/business/project-scope.md` §4 and the clinical-safety pack.
- The live integration run (Phase 8/9) is reproduced manually, not in CI; the gitignored
  `data/` artifacts must be regenerated from a run before this gate can re-execute.
- The single residual operational risk (review-queue backlog, hazard H-11) is owned by the
  deploying organisation and is out of scope for software testing — see
  `docs/clinical-safety/hazard-log.csv`.

## 8. Traceability to the Definition of Done

| DoD item (scope §6) | Evidenced by |
|---|---|
| 1 — validated extraction JSON per referral | `phase4-acceptance.md`, `data/extracted-json/` |
| 2 — patient match computed correctly | `phase5-acceptance.md`, matrix §4 |
| 3 — clean referrals created in OpenMRS & verified | `phase6/8-acceptance.md`, happy-path rows |
| 4 — risky cases routed to human review with a reason code | matrix §4 (Human review class) |
| 5 — a human decision changes the final outcome | `phase9-acceptance.md`, gate check 4 |
| 6 — every action writes an audit row | gate check 6, `data/audit/audit-log.csv` |
| 7 — business vs system exceptions distinct | REF-014 vs REF-015, §3 |
| 8 — idempotent / safely re-runnable | `phase8/9-acceptance.md` (rerun = 0 actioned) |
| 9 — Excel report + dashboard reflect the real run | `phase10-acceptance.md`, `reports/` |
| 10 — clinical-safety + IG docs specific | `phase11-acceptance.md`, `docs/clinical-safety/` |
| 11 — README / demo / CV assets | Phase 13 (next) |
| 12 — no secrets; synthetic notice everywhere | `.env.example`, banners throughout |
