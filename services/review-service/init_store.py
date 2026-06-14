#!/usr/bin/env python3
"""Initialise / refresh the SQLite review store from the Phase 8 review-store.csv.

Idempotent: creates the schema if needed and INSERT-OR-IGNOREs each PENDING row
keyed on referral_id, so re-running never duplicates a review and never clobbers
a decision a clinician has already recorded.

    python init_store.py            # ingest data/review/review-store.csv
    python init_store.py --csv path/to/review-store.csv

ALL DATA IS SYNTHETIC.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import review_store as store  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Ingest the review CSV into SQLite (Phase 9).")
    ap.add_argument("--csv", default=store.DEFAULT_CSV_PATH)
    ap.add_argument("--db", default=store.DEFAULT_DB_PATH)
    args = ap.parse_args()

    if not os.path.exists(args.csv):
        print(f"ERROR: review CSV not found: {args.csv}", file=sys.stderr)
        return 2

    conn = store.connect(args.db)
    result = store.ingest_csv(conn, args.csv)
    result["db"] = args.db
    result["counts"] = store.counts(conn)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
