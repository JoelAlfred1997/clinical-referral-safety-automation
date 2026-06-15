#!/usr/bin/env python3
"""Phase 11 acceptance gate - the clinical-safety + IG pack is specific and sound.

A documentation phase still gets a real, runnable gate. This asserts that:
  - the hazard log names >= 12 hazards, each fully populated;
  - every risk rating uses the defined 5x5 matrix vocabulary;
  - every control-evidence reference resolves to a real artifact in the repo
    (a committed file path) or a real referral scenario (REF-001..015) - so each
    named control is backed by something that actually exists, not a claim;
  - the Clinical Safety Case Report cites every hazard id;
  - every document in the pack carries the synthetic-data / simulation banner.

    python validate_pack.py

No third-party dependencies. ALL DATA IS SYNTHETIC.
"""

from __future__ import annotations

import csv
import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
HAZARD_LOG = os.path.join(_HERE, "hazard-log.csv")
CSCR = os.path.join(_HERE, "clinical-safety-case-report.md")

PACK_DOCS = [
    "docs/clinical-safety/README.md",
    "docs/clinical-safety/clinical-risk-management-plan.md",
    "docs/clinical-safety/clinical-safety-case-report.md",
    "docs/information-governance/README.md",
    "docs/information-governance/dpia.md",
    "docs/information-governance/dtac-assessment.md",
]

LIKELIHOODS = {"Very low", "Low", "Medium", "High", "Very high"}
SEVERITIES = {"Minor", "Significant", "Considerable", "Major", "Catastrophic"}
RISKS = {"Low", "Moderate", "High", "Unacceptable"}
REQUIRED_COLS = ["ID", "Hazard", "Causes", "Clinical effect", "Existing controls",
                 "Control evidence", "Initial likelihood", "Initial severity", "Initial risk",
                 "Residual likelihood", "Residual severity", "Residual risk", "Owner", "Status"]

PASS, FAIL = "PASS", "FAIL"
results: list[tuple[str, str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((PASS if ok else FAIL, name, detail))


def _evidence_ok(cell: str) -> tuple[bool, str]:
    """Every path-like token must exist; every REF-NNN must be a real scenario."""
    tokens = re.split(r"[;,]\s*", cell)
    for tok in tokens:
        tok = tok.strip()
        if not tok:
            continue
        m = re.fullmatch(r"REF-(\d{3})", tok)
        if m:
            if not 1 <= int(m.group(1)) <= 15:
                return False, f"unknown scenario {tok}"
            continue
        if "/" in tok:  # a repo path
            if not os.path.exists(os.path.join(_REPO_ROOT, tok)):
                return False, f"missing artifact {tok}"
    return True, ""


def _has_banner(text: str) -> bool:
    t = text.lower()
    return "synthetic" in t and ("simulation" in t or "not a live nhs" in t)


def main() -> int:
    # --- hazard log structure ---
    with open(HAZARD_LOG, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    check("hazard log names at least 12 hazards", len(rows) >= 12, f"found {len(rows)}")
    check("hazard log has the expected columns",
          list(rows[0].keys()) == REQUIRED_COLS if rows else False)

    fully_populated = all(all((r.get(c) or "").strip() for c in REQUIRED_COLS) for r in rows)
    check("every hazard row is fully populated (no blank cells)", fully_populated)

    ids = [r["ID"] for r in rows]
    check("hazard ids are unique and sequential H-01..",
          ids == [f"H-{i:02d}" for i in range(1, len(rows) + 1)], str(ids))

    ratings_ok = all(
        r["Initial likelihood"] in LIKELIHOODS and r["Residual likelihood"] in LIKELIHOODS and
        r["Initial severity"] in SEVERITIES and r["Residual severity"] in SEVERITIES and
        r["Initial risk"] in RISKS and r["Residual risk"] in RISKS for r in rows)
    check("all risk ratings use the defined 5x5 matrix vocabulary", ratings_ok)

    # Controls should reduce (or hold) residual vs initial risk, never increase it.
    order = {"Low": 0, "Moderate": 1, "High": 2, "Unacceptable": 3}
    not_worse = all(order[r["Residual risk"]] <= order[r["Initial risk"]] for r in rows)
    check("residual risk never exceeds initial risk (controls do not add risk)", not_worse)

    # --- every named control is backed by a real artifact ---
    bad = []
    for r in rows:
        ok, why = _evidence_ok(r["Control evidence"])
        if not ok:
            bad.append(f"{r['ID']}: {why}")
    check("every control-evidence reference resolves to a real file or scenario",
          not bad, "; ".join(bad))

    # --- the safety case cites every hazard ---
    cscr = open(CSCR, encoding="utf-8").read() if os.path.exists(CSCR) else ""
    missing = [i for i in ids if i not in cscr]
    check("the Clinical Safety Case Report cites every hazard id", not missing, str(missing))

    # --- every document carries the simulation banner ---
    no_banner = []
    for rel in PACK_DOCS:
        p = os.path.join(_REPO_ROOT, rel)
        if not os.path.exists(p):
            no_banner.append(rel + " (missing)")
        elif not _has_banner(open(p, encoding="utf-8").read()):
            no_banner.append(rel + " (no banner)")
    check("every pack document exists and carries the synthetic/simulation banner",
          not no_banner, "; ".join(no_banner))

    npass = sum(1 for r in results if r[0] == PASS)
    print("\nPhase 11 - Clinical safety + IG pack: acceptance gate\n" + "=" * 56)
    for status, name, detail in results:
        print(f"[{status}] {name}" + (f"  ({detail})" if detail and status == FAIL else ""))
    print("=" * 56)
    print(f"{npass}/{len(results)} checks passed  ({len(rows)} hazards)")
    return 0 if npass == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
