#!/usr/bin/env python3
"""Build the reporting model from the REAL Phase 8 + Phase 9 run artifacts.

Single source of truth for both the Excel report and the HTML dashboard. It reads
only what the bot actually produced — no hand-typed numbers:

    data/decisions/REF-NNN.decision.json     the bot's decision per referral
    data/extracted-json/REF-NNN.extracted.json   extraction method / confidence
    data/review/review-store.sqlite          the human-review outcomes (Phase 9)
    data/audit/audit-log.csv                 the append-only event trail

and folds them into one per-referral row plus the aggregate counts. Display names
come from the matched patient (or the extracted name, or the filename) — all
synthetic.

ALL DATA IS SYNTHETIC. OpenMRS is a mock EPR/EMR.
"""

from __future__ import annotations

import csv
import json
import os
import sqlite3

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DECISIONS_DIR = os.path.join(_REPO_ROOT, "data", "decisions")
EXTRACTED_DIR = os.path.join(_REPO_ROOT, "data", "extracted-json")
REVIEW_DB = os.path.join(_REPO_ROOT, "data", "review", "review-store.sqlite")
AUDIT_LOG = os.path.join(_REPO_ROOT, "data", "audit", "audit-log.csv")

# Human-readable labels for the terminal outcomes.
FINAL_LABELS = {
    "REFERRAL_CREATED_IN_OPENMRS": "Created in OpenMRS",
    "REVIEW_REJECTED_NO_RECORD": "Rejected at review (no record)",
    "BUSINESS_EXCEPTION_FAILED": "Business exception",
    "SYSTEM_EXCEPTION_ESCALATED": "System exception",
}

# Which reason codes evidence which safety hazard the controls caught.
SAFETY_CATCHES = {
    "Wrong-patient risk": ("MATCH_DOB_MISMATCH", "MATCH_PARTIAL", "MATCH_MULTIPLE_CANDIDATES"),
    "No patient match": ("MATCH_NONE",),
    "Duplicate referral": ("DUPLICATE_REFERRAL",),
    "Urgent / 2WW cancer": ("URGENT_RED_FLAG",),
    "Safeguarding / child": ("SAFEGUARDING", "CHILD_PATIENT"),
    "Incomplete referral": ("INCOMPLETE_MANDATORY_FIELDS",),
    "Low extraction confidence": ("LOW_EXTRACTION_CONFIDENCE",),
    "Not a referral": ("NOT_A_REFERRAL",),
    "File unreadable": ("FILE_UNREADABLE",),
}


def _load_json(path: str) -> dict:
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _name_from_file(source_file: str) -> str:
    # "REF-005-hamilton-partial-match.txt" -> "Hamilton"
    parts = (source_file or "").split("-")
    return parts[2].split(".")[0].capitalize() if len(parts) > 2 else ""


def _load_reviews() -> dict:
    if not os.path.exists(REVIEW_DB):
        return {}
    conn = sqlite3.connect(REVIEW_DB)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM reviews").fetchall()
    except sqlite3.OperationalError:
        return {}
    finally:
        conn.close()
    return {r["referral_id"]: dict(r) for r in rows}


def load_audit_rows() -> list[dict]:
    rows = []
    if not os.path.exists(AUDIT_LOG):
        return rows
    with open(AUDIT_LOG, newline="", encoding="utf-8-sig") as fh:
        for r in csv.reader(fh):
            if len(r) >= 6:
                rows.append({"timestamp": r[0], "referral_id": r[1], "action": r[2],
                             "status": r[3], "match_result": r[4], "detail": r[5]})
    return rows


def build_model() -> dict:
    reviews = _load_reviews()
    referrals = []
    for fname in sorted(os.listdir(DECISIONS_DIR)):
        if not fname.endswith(".decision.json"):
            continue
        d = _load_json(os.path.join(DECISIONS_DIR, fname))
        ref = d["referral_id"]
        ex_path = os.path.join(EXTRACTED_DIR, f"{ref}.extracted.json")
        ex = _load_json(ex_path) if os.path.exists(ex_path) else {}
        mp = d.get("matched_patient") or {}
        exfields = ex.get("extraction") or {}
        name = (" ".join(p for p in (mp.get("first_name"), mp.get("last_name")) if p)
                or " ".join(p for p in (exfields.get("patient_first_name"),
                                        exfields.get("patient_last_name")) if p)
                or _name_from_file(d.get("source_file", "")))
        # NOT_APPLICABLE = no patient (not a referral / unreadable file): don't show
        # a surname guessed from the filename.
        if d.get("match_result") == "NOT_APPLICABLE":
            name = "(n/a)"
        rv = reviews.get(ref, {})
        final_status = rv.get("final_status") or d.get("final_status")
        referrals.append({
            "referral_id": ref,
            "patient_name": name or "(none)",
            "source_file": d.get("source_file", ""),
            "extraction_method": (ex.get("extraction_method")
                                  or d.get("upstream", {}).get("extraction_method") or "-"),
            "confidence": ex.get("confidence") or d.get("upstream", {}).get("confidence") or "-",
            "match_result": d.get("match_result", ""),
            "reason_codes": d.get("reason_codes", []),
            "bot_decision": d.get("bot_decision", ""),
            "reviewer": rv.get("reviewer") or "",
            "reviewer_decision": rv.get("reviewer_decision") or "",
            "rationale": rv.get("rationale") or "",
            "final_status": final_status,
            "final_label": FINAL_LABELS.get(final_status, final_status or "-"),
            "encounter_uuid": rv.get("encounter_uuid") or "",
            "in_openmrs": final_status == "REFERRAL_CREATED_IN_OPENMRS",
        })

    total = len(referrals)
    created = [r for r in referrals if r["final_status"] == "REFERRAL_CREATED_IN_OPENMRS"]
    auto = [r for r in created if r["bot_decision"] == "AUTO_CREATE_REFERRAL_RECORD"]
    human_created = [r for r in created if r["bot_decision"] == "HUMAN_REVIEW_REQUIRED"]
    rejected = [r for r in referrals if r["final_status"] == "REVIEW_REJECTED_NO_RECORD"]
    reviewed = [r for r in referrals if r["bot_decision"] == "HUMAN_REVIEW_REQUIRED"]
    exceptions = [r for r in referrals
                  if r["final_status"] in ("BUSINESS_EXCEPTION_FAILED", "SYSTEM_EXCEPTION_ESCALATED")]

    def counts(key):
        out: dict[str, int] = {}
        for r in referrals:
            out[r[key]] = out.get(r[key], 0) + 1
        return out

    # Safety catches: count referrals whose reason codes hit each hazard family.
    safety = {}
    for label, codes in SAFETY_CATCHES.items():
        n = sum(1 for r in referrals if any(c in r["reason_codes"] for c in codes))
        if n:
            safety[label] = n

    # A referral with a safety flag is NEVER auto-created (the core guarantee).
    auto_with_flag = sum(1 for r in auto if r["reason_codes"] and r["reason_codes"] != ["MATCH_EXACT"])

    return {
        "generated_from": "real Phase 8 + Phase 9 run artifacts",
        "synthetic": True,
        "referrals": referrals,
        "kpis": {
            "total_referrals": total,
            "created_in_openmrs": len(created),
            "auto_created": len(auto),
            "human_approved_created": len(human_created),
            "rejected_no_record": len(rejected),
            "routed_to_human_review": len(reviewed),
            "exceptions": len(exceptions),
            "audit_rows": len(load_audit_rows()),
            "auto_created_with_safety_flag": auto_with_flag,
            "straight_through_pct": round(100 * len(auto) / total) if total else 0,
            "human_in_loop_pct": round(100 * len(reviewed) / total) if total else 0,
        },
        "bot_decision_counts": counts("bot_decision"),
        "final_status_counts": {FINAL_LABELS.get(k, k): v
                                for k, v in counts("final_status").items()},
        "review_outcome_counts": {
            r["reviewer_decision"]: sum(1 for x in reviewed
                                        if x["reviewer_decision"] == r["reviewer_decision"])
            for r in reviewed if r["reviewer_decision"]
        },
        "safety_catches": safety,
        "exceptions": exceptions,
        "human_reviews": reviewed,
        "audit_rows": load_audit_rows(),
    }


if __name__ == "__main__":
    import pprint
    m = build_model()
    pprint.pp(m["kpis"])
    pprint.pp(m["final_status_counts"])
    pprint.pp(m["review_outcome_counts"])
    pprint.pp(m["safety_catches"])
