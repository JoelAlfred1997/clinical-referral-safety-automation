"""Orchestrator: a Phase 4 extraction result -> a validated Phase 5 decision.

Pipeline (architecture steps 6-11, the decision part):
  1. If the document was unreadable / not a referral, short-circuit to the
     System / Business exception branch (no patient match attempted).
  2. Otherwise match the patient against the repository (seed file or OpenMRS).
  3. Apply the deterministic safety rules -> flags, reason codes, decision.
  4. Assemble the decision record and validate it against the JSON schema.

The actual OpenMRS write (AUTO_CREATE) and review-store write (HUMAN_REVIEW)
are Phase 6/8/9; this engine decides the outcome, it does not perform it.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional

from . import __version__
from .matcher import Match, match_patient
from .rules import decide
from .validate import validate_decision

_NO_MATCH_STATUSES = {"FILE_UNREADABLE", "NOT_A_REFERRAL"}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def decide_for_extraction(extraction_result: Dict, repo) -> Dict:
    """Run matching + rules for one extraction result and return a validated decision."""
    extraction = extraction_result.get("extraction") or {}
    status = extraction_result.get("extraction_status")

    # 1-2. Match (skipped for terminal pre-match branches) ----------------
    if status in _NO_MATCH_STATUSES:
        match: Optional[Match] = None
        match_result = "NOT_APPLICABLE"
        matched_patient = None
        candidate_count = 0
    else:
        match = match_patient(extraction, repo)
        match_result = match.match_result
        matched_patient = match.matched_patient
        candidate_count = match.candidate_count

    # 3. Rules ------------------------------------------------------------
    ruling = decide(extraction_result, match)

    # 4. Assemble + validate ---------------------------------------------
    result = {
        "referral_id": extraction_result.get("referral_id"),
        "source_file": extraction_result.get("source_file"),
        "synthetic": True,
        "engine_version": __version__,
        "patient_match_source": getattr(repo, "source", "local-seed"),
        "match_result": match_result,
        "matched_patient": matched_patient,
        "candidate_count": candidate_count,
        "safety_flags": ruling["safety_flags"],
        "reason_codes": ruling["reason_codes"],
        "bot_decision": ruling["bot_decision"],
        "final_status": ruling["final_status"],
        "decision_reasons": ruling["decision_reasons"],
        "upstream": {
            "extraction_status": status,
            "is_referral": extraction_result.get("is_referral"),
            "confidence": extraction_result.get("confidence"),
            "missing_fields": extraction_result.get("missing_fields"),
            "extraction_method": extraction_result.get("extraction_method"),
        },
        "decided_at": _now(),
    }

    ok, errors = validate_decision(result)
    if not ok:
        raise ValueError(
            f"Decision for {result.get('referral_id')} failed schema validation:\n  "
            + "\n  ".join(errors)
        )
    return result
