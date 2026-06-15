# `reports/` — run reporting (Phase 10)

Portfolio reporting generated from the **real** Phase 8 + Phase 9 run by
[`services/reporting/`](../services/reporting/). Regenerate any time:

```bash
python services/reporting/build_all.py
```

| File | Notes |
|---|---|
| `dashboard.html` | Self-contained dashboard (inline CSS + SVG, no JS/network). Open in any browser; screenshot for CV/LinkedIn. **Committed.** |
| `referral-safety-report.xlsx` | Five-sheet Excel workbook (Summary + charts, Referrals, Human review, Exceptions, Audit trail). **Gitignored** (regenerable binary) — build it with the command above. |

> Synthetic data only. OpenMRS is a mock EPR/EMR. Not a live NHS system.
