# Reporting (Phase 10)

Turns the **real** Phase 8 + Phase 9 run into portfolio-ready reporting: an Excel
workbook and a self-contained HTML dashboard. Every figure is derived from the run
artifacts — there are no hand-typed numbers.

## Inputs (the real run)

| Source | Used for |
|---|---|
| `data/decisions/REF-NNN.decision.json` | the bot's decision, match result, reason codes per referral |
| `data/extracted-json/REF-NNN.extracted.json` | extraction method + confidence |
| `data/review/review-store.sqlite` | the Phase 9 human-review outcomes (reviewer, decision, final status, encounter) |
| `data/audit/audit-log.csv` | the append-only event trail (reconciliation) |
| `data/expected-outcomes/REF-NNN.expected.json` | Phase 3 oracles (acceptance cross-check) |

## Pieces

| File | Role |
|---|---|
| `report_model.py` | Single source of truth: folds all artifacts into one per-referral model + aggregate counts (KPIs, outcomes, bot decisions, review outcomes, safety catches). |
| `build_report.py` | Writes `reports/referral-safety-report.xlsx` — Summary (KPIs + pie/bar charts), Referrals, Human review, Exceptions, Audit trail. Needs openpyxl. |
| `build_dashboard.py` | Writes `reports/dashboard.html` — self-contained (inline CSS + inline SVG charts, no JS, no network), opens offline, screenshots cleanly. Stdlib only. |
| `build_all.py` | Runs both. |
| `validate_acceptance.py` | Phase 10 gate (8 checks). |

## Run

```bash
python services/reporting/build_all.py        # both artifacts into reports/
# or individually:
python services/reporting/build_report.py
python services/reporting/build_dashboard.py
python services/reporting/report_model.py      # print the computed KPIs
```

## What the report shows (this run)

15 referrals → **9 created in OpenMRS** (3 fully automated + 6 human-approved/amended),
**4 rejected at review** (no record), **2 exceptions** (1 business, 1 system). 10 routed to
a human (67%); **0 referrals auto-created while carrying a safety flag** — the core guarantee
that the bot never makes a risky clinical decision. 25 append-only audit rows underpin it.

## Acceptance

```bash
python services/reporting/validate_acceptance.py
```
Asserts the model reconciles with the audit log, the outcomes match the headline run,
the safety invariant holds, the bot decisions match the Phase 3 oracles, and both
artifacts are produced and well-formed (Excel has the 5 sheets; the dashboard is
self-contained HTML with inline SVG).

## Scope boundary

Reporting is read-only over data already produced — it creates no OpenMRS records and
makes no decisions. The Excel workbook (`reports/*.xlsx`) is gitignored (regenerable
binary); the HTML dashboard is committed as the portfolio showcase. All data synthetic.
