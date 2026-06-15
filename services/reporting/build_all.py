#!/usr/bin/env python3
"""Generate both reporting artifacts from the real run (Phase 10).

    python build_all.py        # -> reports/referral-safety-report.xlsx + reports/dashboard.html

ALL DATA IS SYNTHETIC.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_dashboard  # noqa: E402
import build_report  # noqa: E402


def main() -> int:
    rc = build_report.main()
    rc = build_dashboard.main() or rc
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
