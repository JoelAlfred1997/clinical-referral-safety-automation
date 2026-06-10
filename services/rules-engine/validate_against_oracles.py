#!/usr/bin/env python3
"""Phase 5 acceptance harness.

Re-extracts every referral (via the Phase 4 extraction CLI), runs the decision
engine against the committed synthetic-patient seed file, and compares the
result to the Phase 3 expected-outcome oracles
(data/expected-outcomes/REF-NNN.expected.json).

Gate checks (what Phase 5 owns), per referral:

  * the decision JSON is schema-valid;
  * match_result      == expected           (EXACT)
  * bot_decision      == expected           (EXACT)
  * final_status      == expected           (EXACT)
  * every expected safety flag   is raised  (COVERAGE)
  * every expected reason code   is present (COVERAGE)
  * the decision carries >=1 reason code    (the headline Phase 5 requirement)
  * if the decision is AUTO_CREATE, NO safety flag is raised (risky -> review)

The three safety-critical categoricals (match / decision / status) are checked
for EXACT equality. Flags and reason codes are checked for COVERAGE: the engine
derives codes mechanically and is deliberately more thorough than the oracle's
hand-written "headline" set, so any EXTRA flag/reason it raises is reported as
INFO, not a failure (the same convention the Phase 4 harness used for REF-013).
Crucially this never weakens the gate: an extra flag on a clean case would flip
its decision away from AUTO_CREATE and fail the EXACT decision check.

Exit code 0 = all gate checks pass.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.decision_engine import decide_for_extraction  # noqa: E402
from src.patient_repository import LocalPatientRepository  # noqa: E402
from src.validate import validate_decision  # noqa: E402

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_ORACLE_DIR = os.path.join(_REPO_ROOT, "data", "expected-outcomes")
_EXTRACTED_DIR = os.path.join(_REPO_ROOT, "data", "extracted-json")
_EXTRACTION_DIR = os.path.join(_REPO_ROOT, "services", "extraction-service")

GREEN, RED, YELLOW, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"


def _regenerate_extractions() -> None:
    """Re-run the Phase 4 extraction CLI so decisions are made on fresh JSON."""
    print(f"{DIM}Re-extracting referrals (Phase 4) for a fresh decision run...{RESET}")
    proc = subprocess.run(
        [sys.executable, "run_extraction.py"],
        cwd=_EXTRACTION_DIR, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr)
        raise SystemExit("Extraction step failed; cannot run the Phase 5 gate.")


def _load_extraction(referral_id: str):
    path = os.path.join(_EXTRACTED_DIR, f"{referral_id}.extracted.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _coverage(label, got_list, expected_list):
    """Every expected item must be present; extras are reported as INFO."""
    got, exp = set(got_list or []), set(expected_list or [])
    missing = sorted(exp - got)
    extra = sorted(got - exp)
    gate = _line(f"{label} cover expected", not missing,
                 f"missing={missing} got={sorted(got)}")
    info = None
    if extra:
        info = _line(f"{label} extra (engine more thorough)", True,
                     f"extra={extra}", info=True)
    return gate, info


def _check(referral_id, oracle, decision):
    gate, info = [], []

    ok, errors = validate_decision(decision)
    gate.append(_line("schema valid", ok, "" if ok else "; ".join(errors)))

    gate.append(_eq("match_result", decision["match_result"], oracle.get("expected_match_result")))
    gate.append(_eq("bot_decision", decision["bot_decision"], oracle.get("expected_bot_decision")))
    gate.append(_eq("final_status", decision["final_status"], oracle.get("expected_final_status")))

    g, i = _coverage("safety_flags", decision["safety_flags"], oracle.get("expected_safety_flags"))
    gate.append(g)
    if i:
        info.append(i)
    g, i = _coverage("reason_codes", decision["reason_codes"], oracle.get("expected_reason_codes"))
    gate.append(g)
    if i:
        info.append(i)

    # Headline Phase 5 invariants.
    gate.append(_line("decision has >=1 reason code", len(decision["reason_codes"]) >= 1,
                      f"reason_codes={decision['reason_codes']}"))
    auto = decision["bot_decision"] == "AUTO_CREATE_REFERRAL_RECORD"
    safe_auto = (not auto) or (len(decision["safety_flags"]) == 0)
    gate.append(_line("auto-create only when no safety flag", safe_auto,
                      f"flags={decision['safety_flags']}"))

    passed = all("PASS" in ln for ln in gate)
    return passed, gate, info


def _eq(label, got, exp, info=False):
    return _line(label, got == exp, f"got={got!r} exp={exp!r}", info=info)


def _line(label, ok, detail="", info=False):
    if info:
        tag = f"{YELLOW}INFO{RESET}"
    else:
        tag = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
    suffix = f"  {DIM}{detail}{RESET}" if (detail and (not ok or info)) else ""
    return f"    [{tag}] {label}{suffix}" if not ok or info else f"    [{tag}] {label}"


def main():
    _regenerate_extractions()
    repo = LocalPatientRepository()

    oracles = sorted(f for f in os.listdir(_ORACLE_DIR) if f.endswith(".expected.json"))
    total = passed = 0
    failures = []

    for fname in oracles:
        with open(os.path.join(_ORACLE_DIR, fname), encoding="utf-8") as fh:
            oracle = json.load(fh)
        referral_id = oracle["referral_id"]
        total += 1

        extraction = _load_extraction(referral_id)
        if extraction is None:
            failures.append(referral_id)
            print(f"\n{referral_id}  [{RED}FAIL{RESET}]  (no extraction JSON)")
            continue

        decision = decide_for_extraction(extraction, repo)
        ok, gate_lines, info_lines = _check(referral_id, oracle, decision)
        status = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
        print(f"\n{referral_id}  [{status}]  ({oracle.get('scenario')})")
        for ln in gate_lines:
            print(ln)
        for ln in info_lines:
            print(ln)
        if ok:
            passed += 1
        else:
            failures.append(referral_id)

    print("\n" + "=" * 64)
    print(f"GATE RESULT: {passed}/{total} referrals pass the decision acceptance")
    if failures:
        print(f"FAILED: {', '.join(failures)}")
    print("=" * 64)
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
