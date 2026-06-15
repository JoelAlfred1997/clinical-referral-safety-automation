# Clinical safety pack

> ⚠️ **Portfolio simulation — synthetic data only. NOT a live NHS system and NOT assured or
> certified clinical software.** These artefacts are *inspired by* DCB0129 / DCB0160 to
> demonstrate clinical-safety thinking; they are not regulatory submissions.

A DCB0129-inspired clinical-safety pack for the Clinical Referral Safety Automation. Unusually
for a documentation set, it is **machine-checked**: every named control points at the real file
or scenario that implements it, and [`validate_pack.py`](validate_pack.py) fails if a reference
no longer resolves — so the safety case stays honest as the code changes.

## Contents

| Document | What it is |
|---|---|
| [`safety-boundary-statement.md`](safety-boundary-statement.md) | The core boundary: synthetic-only, AI-assists-not-decides, mandatory human review, auditable, fail-safe (Phase 0). |
| [`clinical-risk-management-plan.md`](clinical-risk-management-plan.md) | DCB0129-inspired CRMP: scope, roles (simulated CSO), process, the 5 × 5 risk matrix and acceptability criteria. |
| [`hazard-log.csv`](hazard-log.csv) | The formal register — 12 named hazards (H-01..H-12), causes, clinical effect, named controls, **control evidence**, initial vs residual risk. |
| [`clinical-safety-case-report.md`](clinical-safety-case-report.md) | DCB0129-inspired CSCR: system description, hazard summary, controls + evidence, verified safety requirements, residual risk, conclusion. |
| [`validate_pack.py`](validate_pack.py) | The Phase 11 acceptance gate (doc-linter). |

## The core safety argument

**The AI assists; deterministic rules and humans decide; everything is audited; the bot fails
safe.** Concretely, across the 15 synthetic scenarios, **0 referrals were auto-created while
carrying a safety flag** — every wrong-patient, duplicate, urgent, safeguarding, incomplete, or
low-confidence case was routed to a human (Phases 8–10).

## Run the gate

```bash
python docs/clinical-safety/validate_pack.py
```

## Related

Information governance: [`../information-governance/`](../information-governance/) (DPIA + DTAC).
Architecture: [`../technical/architecture.md`](../technical/architecture.md).
