# Phase 12 — Testing + Evidence Pack: Acceptance Record

**Date:** 2026-06-15
**Result:** ✅ PASS — all **15 synthetic referral scenarios** are tested end-to-end and
demonstrated across the **four outcome classes** (happy / human-review / business-exception /
system-exception). Every bot decision matches the independent Phase 3 oracle (**15/15**),
human review changes the outcome in both directions, the core safety invariant holds (**0**
unsafe auto-creates), the run reconciles with the append-only audit log, and **all 11 prior
phase acceptance gates are PASS**. The evidence pack is **generated** from the real artifacts
(no hand-typed figures) and **machine-checked**: `validate_acceptance.py` passes **8/8**.

Delivers Definition-of-Done item **7** — *"Business vs system exceptions are distinct and
handled per REFramework"* — and consolidates the whole-project DoD test evidence (items 1–10).

## What was built

`services/testing/` (stdlib; reuses `services/reporting/report_model.py`):

- **`evidence_model.py`** — the consolidated test result. Fuses the oracles
  (`data/expected-outcomes/`), the bot's real decisions (`data/decisions/`) and the
  post-review resolution (Phase 9) into per-referral evidence rows + roll-ups, and scans
  `docs/testing/phaseN-acceptance.md` for each phase's PASS result. No hand-typed numbers.
- **`build_evidence_pack.py`** → **`docs/testing/evidence-pack.md`** — generated pack:
  consolidated build status (11 gates), headline KPIs, the four outcome classes, and the
  full 15-scenario expected-vs-actual traceability matrix.
- **`validate_acceptance.py`** — the Phase 12 gate (8/8).
- **`README.md`**.

Plus the methodology document **`docs/testing/test-plan.md`** (approach, four outcome
classes, scenario coverage, environment, entry/exit criteria, DoD traceability).

## Headline (the real run)

| Metric | Value |
|---|---|
| Referrals tested end-to-end | 15 |
| Decisions matching the oracle | **15/15** |
| Outcome classes demonstrated | 4/4 (happy 3 · review 10 · BE 1 · SE 1) |
| Human review → created / rejected | 6 / 4 (outcome changed both ways) |
| **Auto-created with a safety flag** | **0** |
| Audit rows | 25 |

## Acceptance gate (machine-checked)

`python services/testing/validate_acceptance.py`:

```
[PASS] all 15 referrals present and tested (15 found)
[PASS] every decision matches the Phase 3 oracle (15/15)
[PASS] all four outcome classes demonstrated (happy/review/BE/SE = 3/10/1/1)
[PASS] human review changes the outcome: 6 approved-in, 4 rejected-out of 10 reviewed
[PASS] safety invariant: 0 referrals auto-created while carrying a safety flag
[PASS] every referral appears in the audit log (25 rows)
[PASS] all 11 prior phase acceptance records are PASS
[PASS] generated evidence pack exists, carries the synthetic banner, and matches the model
8/8 checks passed
```

The standout check is the last one: the committed `evidence-pack.md` is regenerated from the
model and compared byte-for-byte, so the documentation **cannot drift** from the artifacts —
a stale hand edit or a changed run fails the gate.

## How to reproduce

```bash
python services/testing/build_evidence_pack.py     # -> docs/testing/evidence-pack.md
python services/testing/validate_acceptance.py     # -> 8/8 checks passed
```

Depends on a completed Phase 8 + Phase 9 run being present in `data/` (those outputs are
gitignored; regenerate by re-running the bot — see `phase8-acceptance.md` /
`phase9-acceptance.md`).

## Scope boundary

The evidence pack and gate are **read-only** over already-produced artifacts — they create no
OpenMRS records and make no decisions. The pack is a *consolidation and verification* layer,
not a new test of behaviour: the behavioural tests are the per-phase gates it aggregates. All
data synthetic; OpenMRS is a mock EPR/EMR.

## Next — Phase 13

GitHub / CV / LinkedIn packaging: interview-ready README, demo script, STAR stories, and
bullet points.
