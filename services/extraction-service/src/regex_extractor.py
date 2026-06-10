"""Deterministic, dependency-free referral extraction.

This is the *guardrail* path. It does not call any model, so its output is fully
reproducible and auditable -- which is exactly why it is the fallback the safety
story leans on. The optional LLM path (llm_extractor.py) must pass through the
same schema validation and the same confidence/completeness logic.

It targets the synthetic NHS GP referral-letter layout used in
data/input-referrals/ (label lines like "NHS Number:", "Date of birth:", etc.)
and tolerates the deliberately degraded "scanned/faxed" fixture.
"""

from __future__ import annotations

import re
from typing import Dict, Optional

# Leet/OCR substitutions seen in the low-quality scan fixture. Applied only to
# name-like tokens (mostly alphabetic), never to numbers, so we never corrupt an
# NHS number or a date.
_LEET = {"0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "7": "t"}


def _deleet_word(word: str) -> str:
    alpha = sum(c.isalpha() for c in word)
    if alpha >= 2 and any(c.isdigit() for c in word):
        return "".join(_LEET.get(c, c) for c in word)
    return word


def _clean_name(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip(" ,.")
    return " ".join(_deleet_word(w) for w in value.split(" "))


def _value_after_label(text: str, label_pattern: str) -> Optional[str]:
    """Return the trailing text on the first line matching `label_pattern:`."""
    rx = re.compile(label_pattern + r"\s*[:\-]\s*(.+)", re.IGNORECASE)
    for line in text.splitlines():
        m = rx.search(line)
        if m:
            val = m.group(1).strip()
            if val:
                return val
    return None


def _normalise_nhs(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    return digits[:10] if len(digits) >= 10 else None


def _normalise_date(raw: Optional[str]) -> Optional[str]:
    """dd/mm/yyyy | dd-mm-yyyy | with stray spaces  ->  yyyy-mm-dd."""
    if not raw:
        return None
    m = re.search(r"(\d{1,2})\s*[/\-.]\s*(\d{1,2})\s*[/\-.]\s*(\d{4})", raw)
    if not m:
        # also handle digits separated only by spaces e.g. "26 / 03 / 1995"
        m = re.search(r"(\d{1,2})\s+(\d{1,2})\s+(\d{4})", raw)
    if not m:
        return None
    day, month, year = m.group(1), m.group(2), m.group(3)
    try:
        d, mo = int(day), int(month)
    except ValueError:
        return None
    if not (1 <= d <= 31 and 1 <= mo <= 12):
        return None
    return f"{year}-{mo:02d}-{d:02d}"


def _normalise_gender(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    low = raw.strip().lower()
    if low.startswith("m"):
        return "M"
    if low.startswith("f"):
        return "F"
    return None


def normalise_priority(raw: Optional[str]) -> Optional[str]:
    """Map free-text priority onto the controlled vocabulary."""
    if not raw:
        return None
    low = raw.lower()
    if re.search(r"2\s*-?\s*week\s*wait|2ww|two[\s-]*week[\s-]*wait|suspected\s+cancer", low):
        return "2WW"
    if "urgent" in low:
        return "Urgent"
    if "routine" in low:
        return "Routine"
    return None


def _strip_clinician(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    # drop trailing "(GMC 1234567)" and any trailing punctuation/practice tail
    val = re.sub(r"\(.*?\)", "", raw)
    val = val.split(",")[0]
    return _clean_name(val) or None


def _strip_practice(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    # practice line is "<Name>, <City>" -- keep the name part
    val = raw.split(",")[0]
    return _clean_name(val) or None


def _extract_reason(text: str) -> Optional[str]:
    """Grab the reason block from 'Reason for referral:' to the next section."""
    m = re.search(r"reason\s*(?:for\s*referral)?\s*[:]{1,3}\s*", text, re.IGNORECASE)
    if not m:
        return None
    tail = text[m.end():]
    stops = [
        r"\ncurrent medication",
        r"\nallergies",
        r"\nyours sincerely",
        r"\n\s*\(\s*remainder",
        r"\ndr\s",
    ]
    cut = len(tail)
    for s in stops:
        sm = re.search(s, tail, re.IGNORECASE)
        if sm:
            cut = min(cut, sm.start())
    reason = re.sub(r"\s+", " ", tail[:cut]).strip(" ,.")
    return reason or None


def extract_fields(text: str) -> Dict[str, Optional[str]]:
    """Extract the 11 referral fields from raw text. Missing -> None."""
    name_raw = _value_after_label(text, r"(?:patient\s*)?name") or _value_after_label(
        text, r"pt\s*na\s*me"
    )
    first = last = None
    if name_raw:
        cleaned = _clean_name(name_raw)
        parts = cleaned.split(" ")
        if parts:
            first = parts[0]
            last = " ".join(parts[1:]) if len(parts) > 1 else None

    nhs_raw = _value_after_label(text, r"nhs(?:\s*number)?")
    dob_raw = _value_after_label(text, r"(?:date\s*of\s*birth|d\.?o\.?b)")
    gender_raw = _value_after_label(text, r"(?:gender|sex)")
    refdate_raw = _value_after_label(text, r"(?:date\s*of\s*referral|dat3|date)")
    clinician_raw = _value_after_label(text, r"(?:referring\s*(?:gp|clinician)|from|fr0m)")
    practice_raw = _value_after_label(text, r"practice(?!\s*tel)")
    specialty_raw = _value_after_label(text, r"special[a-z]*")
    priority_raw = _value_after_label(text, r"priority")

    return {
        "patient_nhs_number": _normalise_nhs(nhs_raw),
        "patient_first_name": first,
        "patient_last_name": last,
        "patient_dob": _normalise_date(dob_raw),
        "patient_gender": _normalise_gender(gender_raw),
        "referral_date": _normalise_date(refdate_raw),
        "referring_clinician": _strip_clinician(clinician_raw),
        "referring_practice": _strip_practice(practice_raw),
        "specialty": specialty_raw.strip() if specialty_raw else None,
        "priority": normalise_priority(priority_raw),
        "reason_for_referral": _extract_reason(text),
    }


def classify_is_referral(text: str) -> bool:
    """Cheap content classifier: is this document a clinical referral at all?"""
    collapsed = re.sub(r"\s+", " ", text).lower()

    # Explicit self-declaration that it is not a referral wins outright.
    if "not a clinical referral" in collapsed or "not a referral" in collapsed:
        return False

    referral_markers = [
        "reason for referral",
        "referral letter",
        "re ferral",          # degraded scan
        "re ason",            # degraded scan
        "referring gp",
        "speciality",
        "specialty",
        "refer psych",
    ]
    has_referral_content = any(mk in collapsed for mk in referral_markers)

    # An appointment reminder with no referral content is not a referral.
    if "appointment reminder" in collapsed and not has_referral_content:
        return False

    return has_referral_content
