#!/usr/bin/env python3
"""Phase 12 evidence model — the consolidated test result, derived from real artifacts.

This is the single source of truth for the Phase 12 evidence pack and its gate. It
fuses three already-trusted inputs and adds NO hand-typed numbers:

    data/expected-outcomes/REF-NNN.expected.json   the test oracle (expected result)
    data/decisions/REF-NNN.decision.json           the bot's actual deterministic decision
    services.reporting.report_model.build_model()   the post-human-review resolved outcome
                                                     (Phase 9) + KPIs + audit reconciliation

For every one of the 15 synthetic referrals it produces:
  - the expected vs actual match_result, bot_decision and bot final_status,
  - the outcome CLASS (happy / human-review / business-exception / system-exception),
  - the human-review resolution (reviewer + decision + post-human final status),
  - a per-row pass/fail and the supporting evidence files.

It also scans the per-phase acceptance records (docs/testing/phaseN-acceptance.md) so the
pack can report the consolidated gate status across the whole build.

ALL DATA IS SYNTHETIC. OpenMRS is a mock EPR/EMR.
"""

from __future__ import annotations

import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
sys.path.insert(0, os.path.join(_REPO_ROOT, "services", "reporting"))

import report_model  # noqa: E402  (path injected above)

ORACLE_DIR = os.path.join(_REPO_ROOT, "data", "expected-outcomes")
DECISIONS_DIR = os.path.join(_REPO_ROOT, "data", "decisions")
TESTING_DOCS = os.path.join(_REPO_ROOT, "docs", "testing")

# The four outcome classes the Definition of Done requires us to demonstrate.
OUTCOME_CLASS = {
    "AUTO_CREATE_REFERRAL_RECORD": "Happy path (straight-through)",
    "HUMAN_REVIEW_REQUIRED": "Human review",
    "BUSINESS_EXCEPTION": "Business exception",
    "SYSTEM_EXCEPTION": "System exception",
}

# The per-phase acceptance records that make up the consolidated evidence pack.
PHASE_DOCS = [
    (1, "OpenMRS local setup"),
    (2, "Synthetic patient data"),
    (3, "Synthetic referrals + oracles"),
    (4, "Extraction service"),
    (5, "Rules & safety decision engine"),
    (6, "OpenMRS workflow mapping"),
    (7, "REFramework design spec"),
    (8, "UiPath build (live run)"),
    (9, "Human-in-the-loop review"),
    (10, "Reporting + dashboard"),
    (11, "Clinical safety + IG docs"),
]


def _load_json(path: str) -> dict:
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _scenario_keys() -> list[str]:
    return sorted(
        f[: -len(".expected.json")]
        for f in os.listdir(ORACLE_DIR)
        if f.endswith(".expected.json")
    )


def acceptance_doc_status() -> list[dict]:
    """Scan each docs/testing/phaseN-acceptance.md for its declared PASS result."""
    out = []
    for phase, title in PHASE_DOCS:
        path = os.path.join(TESTING_DOCS, f"phase{phase}-acceptance.md")
        exists = os.path.exists(path)
        passed = False
        if exists:
            with open(path, encoding="utf-8") as fh:
                head = fh.read(2000)
            passed = bool(re.search(r"\*\*Result:\*\*\s*✅\s*PASS", head))
        out.append({
            "phase": phase,
            "title": title,
            "doc": f"docs/testing/phase{phase}-acceptance.md",
            "exists": exists,
            "passed": passed,
        })
    return out


def build_evidence() -> dict:
    """Build the per-referral evidence rows + roll-ups from oracle vs actual vs resolved."""
    model = report_model.build_model()
    resolved = {r["referral_id"]: r for r in model["referrals"]}

    rows = []
    for ref in _scenario_keys():
        oracle = _load_json(os.path.join(ORACLE_DIR, f"{ref}.expected.json"))
        decision = _load_json(os.path.join(DECISIONS_DIR, f"{ref}.decision.json"))
        res = resolved.get(ref, {})

        exp = {
            "match_result": oracle.get("expected_match_result"),
            "bot_decision": oracle.get("expected_bot_decision"),
            "final_status": oracle.get("expected_final_status"),
        }
        act = {
            "match_result": decision.get("match_result"),
            "bot_decision": decision.get("bot_decision"),
            "final_status": decision.get("final_status"),  # bot's status, pre-human
        }
        decision_ok = all(exp[k] == act[k] for k in ("match_result", "bot_decision", "final_status"))

        rows.append({
            "referral_id": ref,
            "source_file": decision.get("source_file", ""),
            "scenario": oracle.get("scenario", ""),
            "outcome_class": OUTCOME_CLASS.get(act["bot_decision"], "?"),
            "expected": exp,
            "actual": act,
            "reason_codes": decision.get("reason_codes", []),
            "decision_matches_oracle": decision_ok,
            # post-human-review resolution (Phase 9), if any
            "reviewer": res.get("reviewer", ""),
            "reviewer_decision": res.get("reviewer_decision", ""),
            "resolved_final_status": res.get("final_status", ""),
            "resolved_final_label": res.get("final_label", ""),
            "in_openmrs": res.get("in_openmrs", False),
            "evidence": {
                "extraction": f"data/extracted-json/{ref}.extracted.json",
                "decision": f"data/decisions/{ref}.decision.json",
                "oracle": f"data/expected-outcomes/{ref}.expected.json",
            },
        })

    # Roll up the outcome classes actually demonstrated.
    classes: dict[str, int] = {}
    for r in rows:
        classes[r["outcome_class"]] = classes.get(r["outcome_class"], 0) + 1

    # Human-in-the-loop: did a clinician decision change the outcome? (DoD item 5)
    hitl = [r for r in rows if r["outcome_class"] == "Human review"]
    hitl_created = [r for r in hitl if r["in_openmrs"]]
    hitl_rejected = [r for r in hitl if r["resolved_final_status"] == "REVIEW_REJECTED_NO_RECORD"]

    return {
        "synthetic": True,
        "generated_from": "oracles + real decision artifacts + post-review resolution",
        "rows": rows,
        "total": len(rows),
        "outcome_classes": classes,
        "decisions_matching_oracle": sum(1 for r in rows if r["decision_matches_oracle"]),
        "hitl_total": len(hitl),
        "hitl_created": len(hitl_created),
        "hitl_rejected": len(hitl_rejected),
        "kpis": model["kpis"],
        "acceptance_docs": acceptance_doc_status(),
        "audit_rows": model["audit_rows"],
    }


if __name__ == "__main__":
    import pprint
    ev = build_evidence()
    print(f"total referrals: {ev['total']}")
    print(f"decisions matching oracle: {ev['decisions_matching_oracle']}/{ev['total']}")
    print("outcome classes:")
    pprint.pp(ev["outcome_classes"])
    print(f"HITL: {ev['hitl_total']} reviewed -> {ev['hitl_created']} created, "
          f"{ev['hitl_rejected']} rejected")
    print("acceptance docs:")
    for d in ev["acceptance_docs"]:
        flag = "PASS" if d["passed"] else ("MISSING" if not d["exists"] else "NOT PASS")
        print(f"  phase{d['phase']:>2}  {flag:<7} {d['title']}")
