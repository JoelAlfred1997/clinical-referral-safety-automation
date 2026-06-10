#!/usr/bin/env python3
"""Extract every referral in data/input-referrals/ to data/extracted-json/.

Usage:
    python run_extraction.py                 # all referrals
    python run_extraction.py REF-001 REF-013 # only these ids
    python run_extraction.py --file path.txt # a single file

Writes one REF-NNN.extracted.json per input and prints a one-line summary table.
Reproducible offline: with no API key it uses the deterministic regex path.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# Allow `python run_extraction.py` from the service dir without installing.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.extractor import extract_referral  # noqa: E402

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_INPUT_DIR = os.path.join(_REPO_ROOT, "data", "input-referrals")
_OUTPUT_DIR = os.path.join(_REPO_ROOT, "data", "extracted-json")


def _input_files(ids):
    files = []
    for name in sorted(os.listdir(_INPUT_DIR)):
        if name == ".gitkeep" or name.startswith("."):
            continue
        full = os.path.join(_INPUT_DIR, name)
        if not os.path.isfile(full):
            continue
        if ids and not any(name.upper().startswith(i.upper()) for i in ids):
            continue
        files.append(full)
    return files


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract referral documents to JSON.")
    ap.add_argument("ids", nargs="*", help="Referral ids to process (default: all).")
    ap.add_argument("--file", help="Process a single explicit file path.")
    args = ap.parse_args()

    os.makedirs(_OUTPUT_DIR, exist_ok=True)

    paths = [args.file] if args.file else _input_files(args.ids)
    if not paths:
        print("No matching referral files found.")
        return 1

    print(f"{'REF':<8} {'STATUS':<16} {'IS_REF':<7} {'CONF':<7} {'METHOD':<20} MISSING")
    print("-" * 90)

    failures = 0
    for path in paths:
        try:
            result = extract_referral(path)
        except Exception as exc:  # schema failure etc.
            failures += 1
            print(f"{os.path.basename(path):<8} ERROR: {exc}")
            continue

        out_path = os.path.join(_OUTPUT_DIR, f"{result['referral_id']}.extracted.json")
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2, ensure_ascii=False)
            fh.write("\n")

        missing = result["missing_fields"]
        missing_str = "-" if not missing else ",".join(missing) if missing else "[]"
        if missing == []:
            missing_str = "[]"
        print(
            f"{result['referral_id']:<8} {result['extraction_status']:<16} "
            f"{str(result['is_referral']):<7} {result['confidence']:<7} "
            f"{result['extraction_method']:<20} {missing_str}"
        )

    print("-" * 90)
    print(f"Wrote {len(paths) - failures} file(s) to {os.path.relpath(_OUTPUT_DIR, _REPO_ROOT)}/"
          + (f"  ({failures} error(s))" if failures else ""))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
