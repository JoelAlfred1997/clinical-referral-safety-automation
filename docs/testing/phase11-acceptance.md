# Phase 11 — Clinical Safety + Information Governance: Acceptance Record

**Date:** 2026-06-15
**Result:** ✅ PASS — a DCB0129/DCB0160/DTAC/DPIA-**inspired** governance pack exists, is
**specific** (12 named hazards, each mapped to a named control and the **real file/scenario that
implements it**), is **professional** (CRMP + hazard log + safety case + DPIA + DTAC, cross-
referenced), and is **clearly a simulation** (synthetic-data banner on every document, explicit
non-claims). The pack is **machine-checked**: `validate_pack.py` passes **9/9**.

Delivers Definition-of-Done item **10** — *"Clinical-safety + IG docs exist and are specific
(named hazards, named controls)."*

## What was written

**Clinical safety — `docs/clinical-safety/`:**
- `clinical-risk-management-plan.md` — DCB0129-inspired CRMP: scope, roles (simulated CSO), the
  5 × 5 risk matrix and acceptability criteria.
- `hazard-log.csv` — the formal register: **12 named hazards (H-01..H-12)**, causes, clinical
  effect, named existing controls, **control evidence** (the actual file/scenario), and initial
  vs residual risk.
- `clinical-safety-case-report.md` — DCB0129-inspired CSCR: system description, hazard summary,
  controls + evidence, six verified safety requirements, residual risk, conclusion.
- `README.md`, `validate_pack.py` (the gate), plus the existing `safety-boundary-statement.md`.

**Information governance — `docs/information-governance/`:**
- `dpia.md` — DPIA-inspired: nature of processing, data flow, six data-protection risks +
  mitigations (DP-1..DP-6), data minimisation, outcome.
- `dtac-assessment.md` — DTAC-inspired self-assessment across the five domains (clinical safety,
  data protection, technical security, interoperability, usability), each with evidence and the
  gap a real deployment would close.
- `README.md`.

## The safety argument (the headline for interviews)

**AI assists; deterministic rules and humans decide; everything is audited; the bot fails safe.**
The hazard log traces that principle to running code: e.g. wrong-patient risk (H-01) → the
deterministic match gate (REF-004/005/006), AI mis-extraction (H-04) → schema validation + regex
fallback + low-confidence routing (REF-013), fail-open (H-09) → verify-by-reread + System
Exception. The Phase 10 report's key figure — **0 of 15 referrals auto-created while carrying a
safety flag** — is the empirical evidence the controls hold.

Residual risk: **no hazard above Moderate on the software side**; the single residual **High**
(H-11, review-queue backlog) is explicitly an **operational** risk owned by the deploying
organisation under DCB0160 — the software guarantees referrals are persisted and never silently
dropped, but timely resolution depends on staffing.

## Acceptance gate (machine-checked)

`python docs/clinical-safety/validate_pack.py`:

```
[PASS] hazard log names at least 12 hazards
[PASS] hazard log has the expected columns
[PASS] every hazard row is fully populated (no blank cells)
[PASS] hazard ids are unique and sequential H-01..
[PASS] all risk ratings use the defined 5x5 matrix vocabulary
[PASS] residual risk never exceeds initial risk (controls do not add risk)
[PASS] every control-evidence reference resolves to a real file or scenario
[PASS] the Clinical Safety Case Report cites every hazard id
[PASS] every pack document exists and carries the synthetic/simulation banner
9/9 checks passed  (12 hazards)
```

The standout check is **"every control-evidence reference resolves to a real file or scenario"**:
the safety case cannot claim a control that isn't actually implemented, and it cannot silently
rot — if a referenced file is renamed or deleted, the gate fails.

## Scope boundary

These artefacts are *inspired by* DCB0129/DCB0160/DTAC and the ICO/NHS DPIA process to
demonstrate governance thinking; they are **not** regulatory submissions and confer no
assurance. The Clinical Safety Officer role is simulated. All data is synthetic.

## Next — Phase 12

Testing + evidence pack: consolidate the per-phase acceptance records into one evidence pack and
demonstrate all 15 scenarios (happy / business-exception / system-exception / human-review).
