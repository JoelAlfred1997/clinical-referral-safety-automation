#!/usr/bin/env python3
"""Decide every extracted referral in data/extracted-json/ -> data/decisions/.

Usage:
    python run_decisions.py                  # all extracted referrals
    python run_decisions.py REF-001 REF-007  # only these ids
    python run_decisions.py --source openmrs # match against live OpenMRS REST

Reads data/extracted-json/REF-NNN.extracted.json (produced by the Phase 4
extraction service) and writes data/decisions/REF-NNN.decision.json plus a
one-line summary table.

Reproducible offline: the default --source local matches against the committed
synthetic-patient seed file, so no Docker/network is required.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.decision_engine import decide_for_extraction  # noqa: E402
from src.patient_repository import get_patient_repository  # noqa: E402

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_EXTRACTED_DIR = os.path.join(_REPO_ROOT, "data", "extracted-json")
_OUTPUT_DIR = os.path.join(_REPO_ROOT, "data", "decisions")


def _extracted_files(ids):
    if not os.path.isdir(_EXTRACTED_DIR):
        return []
    files = []
    for name in sorted(os.listdir(_EXTRACTED_DIR)):
        if not name.endswith(".extracted.json"):
            continue
        if ids and not any(name.upper().startswith(i.upper()) for i in ids):
            continue
        files.append(os.path.join(_EXTRACTED_DIR, name))
    return files


def main() -> int:
    ap = argparse.ArgumentParser(description="Decide referral routing from extraction JSON.")
    ap.add_argument("ids", nargs="*", help="Referral ids to process (default: all).")
    ap.add_argument("--source", default="local",
                    help="Patient match source: 'local' (seed file, default) or 'openmrs'.")
    args = ap.parse_args()

    paths = _extracted_files(args.ids)
    if not paths:
        print(f"No extraction JSON found in {os.path.relpath(_EXTRACTED_DIR, _REPO_ROOT)}/.\n"
              "Run the Phase 4 extraction first:  "
              "cd services/extraction-service; python run_extraction.py")
        return 1

    os.makedirs(_OUTPUT_DIR, exist_ok=True)
    repo = get_patient_repository(args.source)

    print(f"Patient match source: {getattr(repo, 'source', args.source)}")
    print(f"{'REF':<8} {'MATCH':<20} {'DECISION':<28} REASONS")
    print("-" * 100)

    failures = 0
    for path in paths:
        with open(path, encoding="utf-8") as fh:
            extraction_result = json.load(fh)
        try:
            decision = decide_for_extraction(extraction_result, repo)
        except Exception as exc:
            failures += 1
            print(f"{os.path.basename(path):<8} ERROR: {exc}")
            continue

        out_path = os.path.join(_OUTPUT_DIR, f"{decision['referral_id']}.decision.json")
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(decision, fh, indent=2, ensure_ascii=False)
            fh.write("\n")

        print(f"{decision['referral_id']:<8} {decision['match_result']:<20} "
              f"{decision['bot_decision']:<28} {','.join(decision['reason_codes'])}")

    print("-" * 100)
    print(f"Wrote {len(paths) - failures} file(s) to {os.path.relpath(_OUTPUT_DIR, _REPO_ROOT)}/"
          + (f"  ({failures} error(s))" if failures else ""))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
