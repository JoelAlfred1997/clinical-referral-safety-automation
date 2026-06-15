# services/testing — Phase 12 consolidated test + evidence pack

> ⚠️ Portfolio simulation. 100% synthetic data. OpenMRS is a mock EPR/EMR.

Phase 12 consolidates the per-phase acceptance records into a single, **generated**
evidence pack and a machine-checked end-to-end gate. Nothing here is hand-typed: every
number is re-derived from the real run artifacts and the Phase 3 test oracles.

## Files

| File | Role |
|---|---|
| `evidence_model.py` | Single source of truth. Fuses the oracles (`data/expected-outcomes/`), the bot's real decisions (`data/decisions/`) and the post-review resolution (Phase 9, via `services/reporting/report_model.py`) into per-referral evidence rows + roll-ups; also scans `docs/testing/phaseN-acceptance.md` for each phase's PASS result. |
| `build_evidence_pack.py` | Renders `docs/testing/evidence-pack.md` from the model (consolidated build status, headline KPIs, the four outcome classes, the 15-scenario traceability matrix). |
| `validate_acceptance.py` | The Phase 12 gate (8/8). Re-derives everything and asserts the Definition of Done for testing — including that the committed pack still matches the model (catches stale hand edits). |

## Run

```bash
python services/testing/build_evidence_pack.py     # -> docs/testing/evidence-pack.md
python services/testing/validate_acceptance.py     # -> 8/8 checks passed
```

The gate is read-only over already-produced artifacts; it creates no OpenMRS records and
makes no decisions. It depends on a completed Phase 8 + Phase 9 run being present in
`data/` (those outputs are gitignored — regenerate by re-running the bot; see
`docs/testing/phase8-acceptance.md` / `phase9-acceptance.md`).

## What it proves

All 15 synthetic referrals run end-to-end across the four outcome classes
(happy / human-review / business-exception / system-exception), every decision matches
its oracle, human review changes the outcome in both directions, the safety invariant
holds (0 unsafe auto-creates), the run reconciles with the audit log, and every prior
phase gate is PASS. See `docs/testing/test-plan.md` and `docs/testing/phase12-acceptance.md`.
