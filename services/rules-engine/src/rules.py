"""Deterministic clinical-safety decision rules (Phase 5).

A pure function: (extraction result, patient Match) -> safety flags, reason
codes, a single bot decision, and the intended final status. NO I/O, NO LLM.

Two invariants this layer guarantees (the Phase 5 acceptance gate):
  1. EVERY decision carries at least one reason code (auditability).
  2. ANY safety flag blocks auto-create -- risky/uncertain/urgent/incomplete/
     duplicate/match-risk always routes to a human. Only a clean, complete,
     exactly-matched, legible, non-urgent, non-duplicate referral auto-creates.

Reason codes are derived MECHANICALLY from the conditions present, so two
referrals with the same conditions always get the same codes. Where a referral
trips several conditions, every one is recorded (e.g. a safeguarding child that
is also marked urgent records SAFEGUARDING, CHILD_PATIENT and URGENT_RED_FLAG) --
the engine is deliberately thorough rather than picking a single "headline".
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .matcher import Match

# Bot decisions / final statuses (kept as constants to avoid typos).
AUTO_CREATE = "AUTO_CREATE_REFERRAL_RECORD"
HUMAN_REVIEW = "HUMAN_REVIEW_REQUIRED"
BUSINESS_EXCEPTION = "BUSINESS_EXCEPTION"
SYSTEM_EXCEPTION = "SYSTEM_EXCEPTION"

_FINAL_STATUS = {
    AUTO_CREATE: "REFERRAL_CREATED_IN_OPENMRS",
    HUMAN_REVIEW: "ROUTED_TO_HUMAN_REVIEW",
    BUSINESS_EXCEPTION: "BUSINESS_EXCEPTION_FAILED",
    SYSTEM_EXCEPTION: "SYSTEM_EXCEPTION_ESCALATED",
}

# match_result -> (safety_flag or None, reason_code)
_MATCH_RULES = {
    "EXACT_MATCH": (None, "MATCH_EXACT"),
    "DOB_MISMATCH": ("PATIENT_MATCH_RISK", "MATCH_DOB_MISMATCH"),
    "PARTIAL_MATCH": ("PATIENT_MATCH_RISK", "MATCH_PARTIAL"),
    "MULTIPLE_CANDIDATES": ("PATIENT_MATCH_RISK", "MATCH_MULTIPLE_CANDIDATES"),
    "NO_MATCH": ("PATIENT_NOT_FOUND", "MATCH_NONE"),
}

# Completeness blockers EXCLUDE patient_nhs_number: a missing identifier is a
# patient-MATCHING concern (it drives PARTIAL/MULTIPLE), not a referral-content
# completeness gap. This is why REF-005/006 are match-risk, not "incomplete".
_NON_COMPLETENESS_FIELDS = {"patient_nhs_number"}


class Decision:
    def __init__(self):
        self.safety_flags: List[str] = []
        self.reason_codes: List[str] = []
        self.decision_reasons: List[str] = []

    def add(self, flag: Optional[str], reason: Optional[str], note: str):
        if flag and flag not in self.safety_flags:
            self.safety_flags.append(flag)
        if reason and reason not in self.reason_codes:
            self.reason_codes.append(reason)
        if note:
            self.decision_reasons.append(note)


def decide(extraction: Dict, match: Optional[Match]) -> Dict:
    """Return the routing decision for one (extraction, match) pair."""
    d = Decision()
    status = extraction.get("extraction_status")

    # --- Terminal, pre-match branches -----------------------------------
    if status == "FILE_UNREADABLE":
        d.add("FILE_UNREADABLE", "FILE_UNREADABLE",
              "File could not be read/parsed: technical fault -> System Exception "
              "(retry per REFramework, screenshot, then escalate).")
        return _finalise(d, SYSTEM_EXCEPTION)

    if extraction.get("is_referral") is False or status == "NOT_A_REFERRAL":
        d.add("NOT_A_REFERRAL", "NOT_A_REFERRAL",
              "Readable document, but not a referral (no referral intent / clinical "
              "content): bad input that retrying will not fix -> Business Exception.")
        return _finalise(d, BUSINESS_EXCEPTION)

    # --- Readable referral: assess every safety condition ---------------
    mr = match.match_result if match else "NO_MATCH"
    flag, reason = _MATCH_RULES.get(mr, ("PATIENT_NOT_FOUND", "MATCH_NONE"))
    match_note = match.notes[0] if (match and match.notes) else ""
    d.add(flag, reason, match_note or f"Patient match result: {mr}.")

    # Duplicate referral: only trust this on a CONFIRMED identity (exact match).
    if mr == "EXACT_MATCH" and match and match.duplicate_active_referral:
        d.add("DUPLICATE_REFERRAL_RISK", "DUPLICATE_REFERRAL",
              f"Patient already has an active {match.matched_specialty} referral and "
              "this referral is for the same speciality = duplicate-referral risk.")

    # Completeness (clinical fields only; NHS number handled by matching).
    missing = extraction.get("missing_fields") or []
    clinical_missing = [f for f in missing if f not in _NON_COMPLETENESS_FIELDS]
    if clinical_missing:
        d.add("INCOMPLETE_REFERRAL", "INCOMPLETE_MANDATORY_FIELDS",
              "Mandatory referral fields missing/non-substantive: "
              + ", ".join(clinical_missing) + ".")

    # Extraction confidence gate (independent of match quality).
    if extraction.get("confidence") == "low":
        d.add("LOW_CONFIDENCE_EXTRACTION", "LOW_EXTRACTION_CONFIDENCE",
              "Extraction confidence is low (degraded scan/fax): values must be "
              "human-verified before any record is created.")

    # Advisory clinical signals (extractor flags them; rules act on them).
    sig = extraction.get("extraction_signals") or {}
    if sig.get("urgent_red_flag"):
        d.add("URGENT_RED_FLAG", "URGENT_RED_FLAG",
              "Urgent / red-flag content: per the safety boundary, urgent referrals "
              "are never auto-created regardless of match quality.")
    if sig.get("suspected_cancer"):
        # Flag only -- the routing reason is the urgent red flag it implies.
        d.add("SUSPECTED_CANCER", None,
              "Suspected-cancer / 2-week-wait content present.")
    if sig.get("safeguarding"):
        d.add("SAFEGUARDING", "SAFEGUARDING",
              "Safeguarding content: must always be handled by a human.")
    if sig.get("child_patient"):
        d.add("CHILD_PATIENT", "CHILD_PATIENT",
              "Paediatric (child) patient: must always be handled by a human.")

    # --- Single decision: any flag => review; otherwise auto-create -----
    bot_decision = HUMAN_REVIEW if d.safety_flags else AUTO_CREATE
    if bot_decision == AUTO_CREATE:
        d.decision_reasons.append(
            "Exact patient match, complete, legible, non-urgent, no duplicate: safe to "
            "auto-create the referral record in OpenMRS (then verify by re-read)."
        )
    return _finalise(d, bot_decision)


def _finalise(d: Decision, bot_decision: str) -> Dict:
    return {
        "safety_flags": d.safety_flags,
        "reason_codes": d.reason_codes,
        "bot_decision": bot_decision,
        "final_status": _FINAL_STATUS[bot_decision],
        "decision_reasons": d.decision_reasons,
    }
