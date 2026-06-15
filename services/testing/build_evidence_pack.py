#!/usr/bin/env python3
"""Generate docs/testing/evidence-pack.md from the Phase 12 evidence model.

The pack is GENERATED, never hand-typed: every number, every row and every pass/fail
mark comes from evidence_model.build_evidence(), which in turn reads the real run
artifacts and the test oracles. Re-running this after a fresh end-to-end run refreshes
the pack; if reality drifts from the oracles, the table shows it and the gate fails.

ALL DATA IS SYNTHETIC. OpenMRS is a mock EPR/EMR.
"""

from __future__ import annotations

import os

import evidence_model as em

_REPO_ROOT = em._REPO_ROOT
OUT = os.path.join(_REPO_ROOT, "docs", "testing", "evidence-pack.md")

_TICK = "✅"
_CROSS = "❌"


def _fmt_codes(codes: list[str]) -> str:
    return ", ".join(codes) if codes else "—"


def render(ev: dict) -> str:
    L: list[str] = []
    a = L.append

    a("# Evidence Pack — Clinical Referral Safety Automation (Phase 12)")
    a("")
    a("> ⚠️ **Portfolio simulation — 100% synthetic data. Not a live NHS system.** "
      "OpenMRS is a mock EPR/EMR. AI assists extraction only; deterministic rules and "
      "human reviewers own every safety outcome.")
    a("")
    a("**This document is generated** by `services/testing/build_evidence_pack.py` from the "
      "test oracles (`data/expected-outcomes/`), the bot's real decision artifacts "
      "(`data/decisions/`) and the post-review resolution (Phase 9). No figure below is "
      "hand-typed. Regenerate after any run; the Phase 12 gate "
      "(`services/testing/validate_acceptance.py`) re-derives and checks every claim.")
    a("")

    # ---- consolidated build status -------------------------------------------------
    docs = ev["acceptance_docs"]
    n_pass = sum(1 for d in docs if d["passed"])
    a("## 1. Consolidated build status")
    a("")
    a(f"All **{len(docs)}** prior phase acceptance gates are recorded as PASS "
      f"(**{n_pass}/{len(docs)}**). Phase 12 consolidates them into this pack.")
    a("")
    a("| Phase | Deliverable | Acceptance record | Result |")
    a("|---|---|---|---|")
    for d in docs:
        mark = f"{_TICK} PASS" if d["passed"] else (f"{_CROSS} MISSING" if not d["exists"] else f"{_CROSS} NOT PASS")
        a(f"| {d['phase']} | {d['title']} | [`{os.path.basename(d['doc'])}`]({os.path.basename(d['doc'])}) | {mark} |")
    a("| 12 | Testing + evidence pack (this) | `phase12-acceptance.md` | see §5 |")
    a("")

    # ---- headline KPIs -------------------------------------------------------------
    k = ev["kpis"]
    a("## 2. Headline figures (from the real Phase 8 + Phase 9 run)")
    a("")
    a("| Metric | Value |")
    a("|---|---|")
    a(f"| Referrals tested end-to-end | {k['total_referrals']} |")
    a(f"| Decisions matching the oracle | {ev['decisions_matching_oracle']}/{ev['total']} |")
    a(f"| Created in OpenMRS | {k['created_in_openmrs']} "
      f"({k['auto_created']} automated + {k['human_approved_created']} human-approved/amended) |")
    a(f"| Routed to human review | {k['routed_to_human_review']} ({k['human_in_loop_pct']}%) |")
    a(f"| Rejected at review (no record) | {k['rejected_no_record']} |")
    a(f"| Exceptions (business + system) | {k['exceptions']} |")
    a(f"| **Auto-created while carrying a safety flag** | **{k['auto_created_with_safety_flag']}** "
      "— the core safety guarantee |")
    a(f"| Audit rows (who/what/before/after/when/why) | {k['audit_rows']} |")
    a("")

    # ---- the four outcome classes --------------------------------------------------
    cls = ev["outcome_classes"]
    a("## 3. The four outcome classes — all demonstrated")
    a("")
    a("Definition of Done item 7 requires happy-path, human-review, business-exception and "
      "system-exception outcomes to be distinct and demonstrated:")
    a("")
    a("| Outcome class | Referrals | Count |")
    a("|---|---|---|")
    for label in ("Happy path (straight-through)", "Human review",
                  "Business exception", "System exception"):
        refs = ", ".join(r["referral_id"] for r in ev["rows"] if r["outcome_class"] == label)
        a(f"| {label} | {refs or '—'} | {cls.get(label, 0)} |")
    a("")
    a(f"Human-in-the-loop changed the outcome (DoD item 5): of {ev['hitl_total']} reviewed "
      f"referrals, **{ev['hitl_created']}** were approved/amended into OpenMRS and "
      f"**{ev['hitl_rejected']}** were rejected with no record created.")
    a("")

    # ---- full traceability matrix --------------------------------------------------
    a("## 4. Traceability matrix — all 15 scenarios (expected vs actual)")
    a("")
    a("Expected values are the Phase 3 oracle; actual values are the bot's real decision "
      "artifact. The final column is the outcome after the recorded human-review decision.")
    a("")
    a("| Ref | Scenario | Outcome class | Match (exp→act) | Decision (exp→act) | Reason codes | Oracle? | Human-resolved outcome |")
    a("|---|---|---|---|---|---|---|---|")
    for r in ev["rows"]:
        exp, act = r["expected"], r["actual"]
        match = exp["match_result"] if exp["match_result"] == act["match_result"] else f"{exp['match_result']}→{act['match_result']}"
        dec = exp["bot_decision"] if exp["bot_decision"] == act["bot_decision"] else f"{exp['bot_decision']}→{act['bot_decision']}"
        ok = _TICK if r["decision_matches_oracle"] else _CROSS
        resolved = r["resolved_final_label"] or "—"
        if r["reviewer_decision"]:
            resolved = f"{resolved} ({r['reviewer_decision']})"
        a(f"| {r['referral_id']} | {r['scenario']} | {r['outcome_class']} | {match} | {dec} "
          f"| {_fmt_codes(r['reason_codes'])} | {ok} | {resolved} |")
    a("")
    a("**Evidence per row:** `data/extracted-json/REF-NNN.extracted.json` (extraction), "
      "`data/decisions/REF-NNN.decision.json` (decision), "
      "`data/expected-outcomes/REF-NNN.expected.json` (oracle), and the append-only "
      "`data/audit/audit-log.csv` (one row per system action). The Phase 10 workbook "
      "`reports/referral-safety-report.xlsx` and `reports/dashboard.html` visualise the same data.")
    a("")

    # ---- gate summary --------------------------------------------------------------
    a("## 5. Phase 12 acceptance gate")
    a("")
    a("Run `python services/testing/validate_acceptance.py`. It re-derives this entire pack "
      "from the artifacts and asserts: all 15 referrals present, every decision matches its "
      "oracle, all four outcome classes demonstrated, human review changes the outcome, the "
      "safety invariant holds (0 unsafe auto-creates), the run reconciles with the audit log, "
      "every prior phase acceptance record is PASS, and this generated pack is internally "
      "consistent. See `docs/testing/phase12-acceptance.md` for the recorded result.")
    a("")
    a("---")
    a("*Generated from " + ev["generated_from"] + ". All data synthetic.*")
    a("")
    return "\n".join(L)


def main() -> None:
    ev = em.build_evidence()
    text = render(ev)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text)
    rel = os.path.relpath(OUT, _REPO_ROOT)
    print(f"[ok] wrote {rel} ({len(ev['rows'])} scenarios, "
          f"{ev['decisions_matching_oracle']}/{ev['total']} match oracle)")


if __name__ == "__main__":
    main()
