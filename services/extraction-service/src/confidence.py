"""Completeness, confidence and advisory-signal logic.

These functions are shared by BOTH the regex and LLM paths, so confidence is
computed the same way regardless of how the fields were obtained.

Design rules (derived from the Phase 3 oracles):
  * A field is "mandatory" for completeness if its absence should block an
    auto-create: nhs number, specialty, priority, reason. Name/DOB/gender are
    always present in-scope and are not completeness blockers here.
  * Confidence is about *extraction quality*, NOT completeness. A perfectly
    legible but incomplete referral is still high-confidence (REF-012); a
    legible referral missing only its identifier drops to medium because the
    identity is less certain (REF-005/006); a degraded scan drops to low
    (REF-013).
  * Advisory signals (urgent/cancer/safeguarding/child) are hints for the
    Phase 5 rules engine. The extractor never routes or decides on them.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Dict, List, Optional, Tuple

MANDATORY_FIELDS = [
    "patient_nhs_number",
    "specialty",
    "priority",
    "reason_for_referral",
]

# Courtesy / filler words that carry no clinical meaning. Used to decide whether
# a "reason for referral" actually says anything.
_COURTESY = {
    "please", "see", "advise", "advice", "thank", "thanks", "you", "and",
    "kind", "regards", "yours", "sincerely", "the", "for", "your", "attention",
    "to", "a", "this", "patient", "pt", "grateful", "review",
}


def is_substantive_reason(reason: Optional[str]) -> bool:
    """True if the reason contains real clinical content, not just pleasantries."""
    if not reason:
        return False
    words = re.findall(r"[a-zA-Z]+", reason.lower())
    meaningful = [w for w in words if w not in _COURTESY and len(w) > 2]
    return len(meaningful) >= 3


def compute_missing_fields(extraction: Dict[str, Optional[str]]) -> List[str]:
    """Mandatory fields that are absent or (for the reason) non-substantive."""
    missing: List[str] = []
    for field in MANDATORY_FIELDS:
        value = extraction.get(field)
        if field == "reason_for_referral":
            if not is_substantive_reason(value):
                missing.append(field)
        elif not value:
            missing.append(field)
    return missing


_LOW_QUALITY_MARKERS = [
    "poor quality",
    "illeg",          # illegible / illeg ible
    "not legible",
    "scanned",
    "faxed",
    "hand writ",      # handwriting / hand writ ing
    "handwriting unclear",
]


def detect_low_quality(text: str) -> Tuple[bool, List[str]]:
    """Detect a degraded scan/fax that warrants human verification."""
    collapsed = re.sub(r"\s+", " ", text).lower()
    hits = [mk for mk in _LOW_QUALITY_MARKERS if mk in collapsed]
    return (bool(hits), hits)


def compute_confidence(
    text: str,
    extraction: Dict[str, Optional[str]],
    is_referral: bool,
) -> Tuple[str, Optional[float], List[str]]:
    """Return (category, numeric_score, reasons)."""
    if not is_referral:
        return ("n/a", None, ["document is not a referral"])

    low_quality, markers = detect_low_quality(text)
    if low_quality:
        return ("low", 0.35, ["degraded scan/fax markers: " + ", ".join(markers)])

    if not extraction.get("patient_nhs_number"):
        return (
            "medium",
            0.6,
            ["NHS number not supplied; patient identity relies on demographics only"],
        )

    return ("high", 0.95, ["identifier present and text legible"])


def _age_years(dob_iso: Optional[str], on_iso: Optional[str]) -> Optional[int]:
    if not dob_iso:
        return None
    try:
        dob = date.fromisoformat(dob_iso)
        ref = date.fromisoformat(on_iso) if on_iso else date.today()
    except ValueError:
        return None
    return ref.year - dob.year - ((ref.month, ref.day) < (dob.month, dob.day))


def detect_signals(text: str, extraction: Dict[str, Optional[str]]) -> Dict[str, Optional[bool]]:
    """Advisory, NON-authoritative text hints for the Phase 5 rules engine."""
    collapsed = re.sub(r"\s+", " ", text).lower()

    suspected_cancer = bool(
        re.search(r"suspected\s+(lung\s+)?cancer|malignancy|2\s*-?\s*week\s*wait|2ww", collapsed)
    )
    # Drive the urgent flag off the normalised priority and unambiguous urgency
    # cues. Deliberately NOT a bare "red flag" text scan -- letters often say
    # "no red-flag features", which must not trip the signal.
    urgent_red_flag = (
        suspected_cancer
        or extraction.get("priority") in {"Urgent", "2WW"}
        or "expedite" in collapsed
    )
    safeguarding = "safeguarding" in collapsed

    age = _age_years(extraction.get("patient_dob"), extraction.get("referral_date"))
    child_patient = None if age is None else age < 18

    return {
        "urgent_red_flag": urgent_red_flag,
        "suspected_cancer": suspected_cancer,
        "safeguarding": safeguarding,
        "child_patient": child_patient,
    }
