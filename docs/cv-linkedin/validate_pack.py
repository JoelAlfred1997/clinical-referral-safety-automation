#!/usr/bin/env python3
"""Phase 13 acceptance gate — verifies the GitHub/CV/LinkedIn packaging is complete,
self-consistent, and not drifting from the project's real evidence.

Stdlib only. Run from anywhere:  python docs/cv-linkedin/validate_pack.py

Checks (each prints PASS/FAIL; exit code 0 only if all pass):
  1. All required packaging deliverables exist.
  2. Every cv-linkedin markdown file carries the synthetic-data banner.
  3. The top-level README phase table is complete (Phase 13 present, no pending rows).
  4. Every relative link inside the cv-linkedin docs resolves to a real file.
  5. The headline figures quoted in the CV assets match the generated evidence pack
     (no hand-typed numbers that disagree with the source of truth).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# repo root = two levels up from this file (docs/cv-linkedin/validate_pack.py)
ROOT = Path(__file__).resolve().parents[2]
CV = ROOT / "docs" / "cv-linkedin"

REQUIRED = [
    CV / "README.md",
    CV / "demo-script.md",
    CV / "star-stories.md",
    CV / "cv-linkedin-bullets.md",
    CV / "interview-qa.md",
]

# Canonical headline figures — the single source of truth is the generated evidence pack.
# Each entry is a human-readable label and the exact substring that must appear both in the
# evidence pack AND in the CV-facing assets that quote it.
CANONICAL = [
    ("referrals tested", "15"),
    ("decisions vs oracle", "15/15"),
    ("created in OpenMRS", "9"),
    ("unsafe auto-creates", "0"),
]

results: list[tuple[bool, str]] = []


def check(ok: bool, msg: str) -> None:
    results.append((bool(ok), msg))


# --- 1. required files exist -------------------------------------------------
missing = [p.relative_to(ROOT).as_posix() for p in REQUIRED if not p.is_file()]
check(not missing, f"Required deliverables present ({len(REQUIRED)})"
      + (f" — MISSING: {missing}" if missing else ""))

# --- 2. synthetic-data banner on every cv-linkedin doc ----------------------
banner_needle = "synthetic data"
no_banner = []
for p in CV.glob("*.md"):
    txt = p.read_text(encoding="utf-8", errors="replace").lower()
    if banner_needle not in txt or "portfolio simulation" not in txt:
        no_banner.append(p.name)
check(not no_banner, "Synthetic-data banner on every cv-linkedin doc"
      + (f" — MISSING on: {no_banner}" if no_banner else ""))

# --- 3. top-level README phase table complete -------------------------------
readme = (ROOT / "README.md").read_text(encoding="utf-8", errors="replace")
has_p13_done = bool(re.search(r"\|\s*13[^|]*\|[^|]*(complete|✅)", readme, re.IGNORECASE))
no_pending = "⬜" not in readme
check(has_p13_done and no_pending,
      "README phase table complete (Phase 13 done, no pending rows)"
      + ("" if (has_p13_done and no_pending)
         else f" — phase13_done={has_p13_done} no_pending={no_pending}"))

# --- 4. relative links inside cv-linkedin docs resolve ----------------------
link_re = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
broken: list[str] = []
for p in CV.glob("*.md"):
    base = p.parent
    for m in link_re.finditer(p.read_text(encoding="utf-8", errors="replace")):
        target = m.group(1).strip()
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        target = target.split("#", 1)[0].strip()
        if not target:
            continue
        resolved = (base / target).resolve()
        if not resolved.exists():
            broken.append(f"{p.name} -> {target}")
check(not broken, "All relative links in cv-linkedin docs resolve"
      + (f" — BROKEN: {broken}" if broken else ""))

# --- 5. headline figures match the generated evidence pack ------------------
pack_path = ROOT / "docs" / "testing" / "evidence-pack.md"
if not pack_path.is_file():
    check(False, "Evidence pack present for figure cross-check — MISSING evidence-pack.md")
else:
    pack = pack_path.read_text(encoding="utf-8", errors="replace")
    bullets = (CV / "cv-linkedin-bullets.md").read_text(encoding="utf-8", errors="replace")
    demo = (CV / "demo-script.md").read_text(encoding="utf-8", errors="replace")
    bad = []
    for label, needle in CANONICAL:
        in_pack = needle in pack
        in_assets = (needle in bullets) and (needle in demo)
        if not (in_pack and in_assets):
            bad.append(f"{label}='{needle}' (pack={in_pack}, assets={in_assets})")
    check(not bad, f"Headline figures consistent with evidence pack ({len(CANONICAL)})"
          + (f" — MISMATCH: {bad}" if bad else ""))

# --- report -----------------------------------------------------------------
passed = sum(1 for ok, _ in results if ok)
total = len(results)
print("Phase 13 packaging acceptance gate")
print("=" * 60)
for ok, msg in results:
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")
print("=" * 60)
print(f"Result: {passed}/{total} {'PASS' if passed == total else 'FAIL'}")
sys.exit(0 if passed == total else 1)
