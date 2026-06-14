#!/usr/bin/env python3
"""The human-in-the-loop review store (Phase 9).

A *real* store: SQLite (stdlib `sqlite3`), not a flat CSV. It owns the lifecycle
of every referral the bot routed to a human in Phase 8:

    PENDING  ->  DECIDED  ->  RESOLVED        (happy path)
                          ->  FAILED          (system fault while applying)

- PENDING  : routed to review by the bot; awaiting a clinician.
- DECIDED  : a clinician recorded a decision (APPROVE / REJECT / AMEND) with
             their identity and a rationale (the auditable "who" and "why").
- RESOLVED : the bot re-read the decision and applied the outcome
             (APPROVE/AMEND -> create in OpenMRS; REJECT -> no record).
- FAILED   : applying an approval hit a system fault (e.g. OpenMRS down);
             stays actionable so a re-run retries it.

The store row itself is the human-decision audit trail (who / what / before /
after / when / why); `resolve_reviews.py` additionally appends a row to the
append-only audit log for each outcome.

Idempotent throughout: ingest is INSERT-OR-IGNORE keyed on referral_id, and the
resolver only acts on rows not already RESOLVED.

ALL DATA IS SYNTHETIC. OpenMRS is a mock EPR/EMR.
"""

from __future__ import annotations

import csv
import json
import os
import sqlite3
from datetime import datetime, timezone

# Lifecycle states.
PENDING = "PENDING"
DECIDED = "DECIDED"
RESOLVED = "RESOLVED"
FAILED = "FAILED"

# Reviewer decisions.
APPROVE = "APPROVE"   # confirmed safe -> create the referral record in OpenMRS
REJECT = "REJECT"     # not safe / duplicate / no patient -> no record, return to referrer
AMEND = "AMEND"       # correct/complete the referral, then create
VALID_DECISIONS = (APPROVE, REJECT, AMEND)

# Final outcomes (extends the Phase 3 final_status vocabulary).
FINAL_CREATED = "REFERRAL_CREATED_IN_OPENMRS"
FINAL_REJECTED = "REVIEW_REJECTED_NO_RECORD"
FINAL_FAILED = "REVIEW_RESOLUTION_FAILED"

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DEFAULT_DB_PATH = os.path.join(_REPO_ROOT, "data", "review", "review-store.sqlite")
DEFAULT_CSV_PATH = os.path.join(_REPO_ROOT, "data", "review", "review-store.csv")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS reviews (
    referral_id          TEXT PRIMARY KEY,
    source_file          TEXT,
    match_result         TEXT,
    original_decision    TEXT,           -- HUMAN_REVIEW_REQUIRED (what the bot decided)
    reason_codes         TEXT,           -- pipe-delimited, why it was routed
    routed_status        TEXT,           -- ROUTED_TO_HUMAN_REVIEW
    review_status        TEXT NOT NULL DEFAULT 'PENDING',
    reviewer             TEXT,
    reviewer_decision    TEXT,           -- APPROVE / REJECT / AMEND
    rationale            TEXT,
    confirmed_nhs_number TEXT,           -- identity the reviewer confirmed (approvals)
    amended_fields       TEXT,           -- JSON of corrected referral fields (AMEND)
    final_status         TEXT,           -- outcome after the bot applies the decision
    encounter_uuid       TEXT,           -- OpenMRS encounter created, if any
    routed_utc           TEXT,           -- when the bot routed it (from Phase 8)
    created_utc          TEXT,           -- when this row entered the store
    decided_utc          TEXT,
    resolved_utc         TEXT
);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def connect(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.executescript(_SCHEMA)
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    if d.get("amended_fields"):
        try:
            d["amended_fields"] = json.loads(d["amended_fields"])
        except (TypeError, ValueError):
            pass
    return d


# ── Ingest (idempotent) ────────────────────────────────────────────────────

def ingest_csv(conn: sqlite3.Connection, csv_path: str = DEFAULT_CSV_PATH) -> dict:
    """Load the Phase 8 review-store.csv PENDING rows into the store.

    INSERT OR IGNORE keyed on referral_id: re-running never duplicates a review
    and never overwrites a row a reviewer has already touched.

    CSV columns: routed_utc, referral_id, match_result, routed_status,
                 reason_codes, status(PENDING).
    """
    inserted, skipped = 0, 0
    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        for parts in csv.reader(fh):
            if not parts or len(parts) < 6:
                continue
            routed_utc, ref_id, match_result, routed_status, reason_codes, _status = parts[:6]
            cur = conn.execute(
                """INSERT OR IGNORE INTO reviews
                   (referral_id, source_file, match_result, original_decision,
                    reason_codes, routed_status, review_status, routed_utc, created_utc)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (ref_id.strip(), _source_file_for(ref_id.strip()), match_result.strip(),
                 "HUMAN_REVIEW_REQUIRED", reason_codes.strip().strip('"'),
                 routed_status.strip(), PENDING, routed_utc.strip(), utcnow()),
            )
            if cur.rowcount:
                inserted += 1
            else:
                skipped += 1
    conn.commit()
    return {"inserted": inserted, "skipped": skipped}


def _source_file_for(referral_id: str) -> str:
    """Best-effort original filename, read from the saved decision JSON if present."""
    path = os.path.join(_REPO_ROOT, "data", "decisions", f"{referral_id}.decision.json")
    try:
        with open(path, encoding="utf-8-sig") as fh:
            return json.load(fh).get("source_file", "")
    except (OSError, ValueError):
        return ""


# ── Queries ────────────────────────────────────────────────────────────────

def list_reviews(conn: sqlite3.Connection, status: str | None = None) -> list[dict]:
    if status:
        rows = conn.execute(
            "SELECT * FROM reviews WHERE review_status=? ORDER BY referral_id", (status,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM reviews ORDER BY referral_id").fetchall()
    return [_row_to_dict(r) for r in rows]


def get(conn: sqlite3.Connection, referral_id: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM reviews WHERE referral_id=?", (referral_id,)
    ).fetchone()
    return _row_to_dict(row) if row else None


def counts(conn: sqlite3.Connection) -> dict:
    rows = conn.execute(
        "SELECT review_status, COUNT(*) c FROM reviews GROUP BY review_status"
    ).fetchall()
    return {r["review_status"]: r["c"] for r in rows}


# ── Mutations (state machine) ───────────────────────────────────────────────

class ReviewError(ValueError):
    """Invalid reviewer action (bad transition or missing required input)."""


def record_decision(conn: sqlite3.Connection, referral_id: str, *, reviewer: str,
                    decision: str, rationale: str, confirmed_nhs_number: str | None = None,
                    amended_fields: dict | None = None) -> dict:
    """Record a clinician's decision on a PENDING (or already-DECIDED) review.

    Enforces the auditable inputs: a named reviewer, a recognised decision, and a
    rationale are all mandatory; AMEND requires the corrected fields. A decision
    may be revised while still PENDING/DECIDED (the new decision overwrites), but
    not after the bot has RESOLVED it.
    """
    decision = (decision or "").strip().upper()
    if decision not in VALID_DECISIONS:
        raise ReviewError(f"decision must be one of {VALID_DECISIONS}, got {decision!r}")
    if not (reviewer or "").strip():
        raise ReviewError("reviewer (the clinician's identity) is required")
    if not (rationale or "").strip():
        raise ReviewError("rationale (why) is required for the audit trail")
    if decision == AMEND and not amended_fields:
        raise ReviewError("AMEND requires amended_fields (the corrected referral values)")

    row = get(conn, referral_id)
    if row is None:
        raise ReviewError(f"no review found for {referral_id}")
    if row["review_status"] in (RESOLVED,):
        raise ReviewError(
            f"{referral_id} is already RESOLVED ({row['final_status']}); cannot re-decide")

    conn.execute(
        """UPDATE reviews
           SET review_status=?, reviewer=?, reviewer_decision=?, rationale=?,
               confirmed_nhs_number=?, amended_fields=?, decided_utc=?,
               final_status=NULL, encounter_uuid=NULL, resolved_utc=NULL
           WHERE referral_id=?""",
        (DECIDED, reviewer.strip(), decision, rationale.strip(),
         (confirmed_nhs_number or None),
         json.dumps(amended_fields) if amended_fields else None,
         utcnow(), referral_id),
    )
    conn.commit()
    return get(conn, referral_id)


def mark_resolved(conn: sqlite3.Connection, referral_id: str, *, final_status: str,
                  encounter_uuid: str | None = None) -> dict:
    conn.execute(
        """UPDATE reviews SET review_status=?, final_status=?, encounter_uuid=?,
               resolved_utc=? WHERE referral_id=?""",
        (RESOLVED, final_status, encounter_uuid, utcnow(), referral_id),
    )
    conn.commit()
    return get(conn, referral_id)


def mark_failed(conn: sqlite3.Connection, referral_id: str, *, final_status: str) -> dict:
    conn.execute(
        """UPDATE reviews SET review_status=?, final_status=?, resolved_utc=?
           WHERE referral_id=?""",
        (FAILED, final_status, utcnow(), referral_id),
    )
    conn.commit()
    return get(conn, referral_id)
