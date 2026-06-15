# Phase 10 — Reporting + Dashboard: Acceptance Record

**Date:** 2026-06-15
**Result:** ✅ PASS — an Excel workbook and a self-contained HTML dashboard are generated
**entirely from the real Phase 8 + Phase 9 run artifacts** (no hand-typed figures). The
reporting reconciles with the append-only audit log and the Phase 3 oracles, and surfaces the
core safety story: of 15 referrals, **9 were created in OpenMRS** (3 fully automated + 6
human-approved), **4 were rejected at review**, **2 were exceptions**, and **0 were
auto-created while carrying a safety flag**. Self-contained gate: **8/8**.

This delivers Definition-of-Done item **9** — *"Excel report + optional dashboard reflect the
real run."*

## What was built

`services/reporting/` (stdlib + openpyxl for the workbook):

- **`report_model.py`** — the single source of truth. Folds the run artifacts into one
  per-referral model plus aggregate counts:
  - `data/decisions/REF-NNN.decision.json` (bot decision / match / reason codes),
  - `data/extracted-json/REF-NNN.extracted.json` (extraction method / confidence),
  - `data/review/review-store.sqlite` (Phase 9 human-review outcomes),
  - `data/audit/audit-log.csv` (reconciliation),
  - `data/expected-outcomes/REF-NNN.expected.json` (oracle cross-check).
- **`build_report.py`** → `reports/referral-safety-report.xlsx` — five sheets: **Summary**
  (KPI table + outcomes pie + safety-catch bar chart), **Referrals** (per-referral detail),
  **Human review** (the 10 clinician decisions), **Exceptions** (BE/SE), **Audit trail**
  (25 rows). Colour-coded outcomes.
- **`build_dashboard.py`** → `reports/dashboard.html` — a self-contained dashboard (inline CSS
  + inline SVG donut/bars, no JavaScript, no network) that opens offline and screenshots
  cleanly: KPI cards, final-outcomes donut, human-review breakdown, safety hazards caught,
  and the per-referral table.
- **`build_all.py`**, **`validate_acceptance.py`**.

## Headline figures (from the real run)

| Metric | Value |
|---|---|
| Referrals processed | 15 |
| Created in OpenMRS | **9** (3 automated + 6 human-approved/amended) |
| Routed to human review | 10 (67%) |
| Rejected at review (no record) | 4 |
| Exceptions | 2 (1 business, 1 system) |
| **Auto-created with a safety flag** | **0** — the bot never makes a risky clinical call |
| Audit rows | 25 |

Safety hazards caught and routed to a human: wrong-patient risk ×3, no-match ×2, duplicate ×1,
urgent/2WW ×2, safeguarding/child ×1, incomplete ×2, low-confidence ×1, not-a-referral ×1,
file-unreadable ×1.

## Acceptance gate (self-contained)

`python services/reporting/validate_acceptance.py`:

```
[PASS] model covers all 15 referrals
[PASS] outcomes: 9 created (3 auto + 6 human-approved), 4 rejected, 2 exceptions
[PASS] safety invariant: 0 referrals auto-created with a safety flag
[PASS] reconciles with audit log: created count matches the audit trail
[PASS] every referral appears in the audit trail
[PASS] bot decisions match the Phase 3 oracles
[PASS] excel: opens with the 5 expected sheets
[PASS] dashboard: self-contained HTML with inline SVG charts and the headline figures
8/8 checks passed
```

## Defect fixed in this phase (carried from Phase 9)

The Phase 9 resolver wrote audit rows to the shared `data/audit/audit-log.csv` regardless of
which store it ran against, so the acceptance-gate replays (temp DBs) had polluted the real
audit log (55 rows). `resolve_reviews.resolve()` now takes an `audit_log` path; the gate points
it at a throwaway file. The canonical audit log was restored to **25 rows** (15 Phase 8 + the 10
headline Phase 9 rows) before reporting was built on it.

## How to reproduce

```bash
python services/reporting/build_all.py        # -> reports/dashboard.html + referral-safety-report.xlsx
python services/reporting/validate_acceptance.py
```

## Screenshots to capture (portfolio)

- `reports/dashboard.html` open in a browser (KPI cards + outcomes donut + safety bars).
- The Excel **Summary** sheet (KPI table + pie + bar charts).
- The Excel **Audit trail** sheet (25 rows).

## Scope boundary

Reporting is read-only over data already produced — it creates no OpenMRS records and makes no
decisions. The `.xlsx` is gitignored (regenerable binary); `dashboard.html` is committed as the
portfolio showcase. All data synthetic.

## Next — Phase 11

Clinical-safety + information-governance documentation pack (DCB0129/0160/DTAC/DPIA-inspired):
named hazards, named controls, clearly a simulation.
