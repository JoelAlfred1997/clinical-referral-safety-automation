"""Orchestrator: referral file -> validated extraction result.

Pipeline (mirrors the architecture doc, steps 3-5):
  1. Read text (TXT/PDF). Unread -> FILE_UNREADABLE (system-exception input).
  2. Classify referral vs not-a-referral (business-exception input).
  3. Extract fields -- LLM path if enabled, else regex; LLM failure falls back
     to regex. Both paths go through the same normalisers.
  4. Compute missing_fields + confidence + advisory signals.
  5. Validate against the JSON schema before returning.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Dict, Optional

from . import __version__, confidence as conf, regex_extractor as rx
from .llm_extractor import LLMUnavailable, extract_fields_llm, llm_enabled
from .text_reader import FileUnreadableError, read_referral_text
from .validate import validate_result

_EMPTY_EXTRACTION = {
    "patient_nhs_number": None,
    "patient_first_name": None,
    "patient_last_name": None,
    "patient_dob": None,
    "patient_gender": None,
    "referral_date": None,
    "referring_clinician": None,
    "referring_practice": None,
    "specialty": None,
    "priority": None,
    "reason_for_referral": None,
}


def _referral_id(filename: str) -> str:
    m = re.match(r"(REF-\d{3})", filename, re.IGNORECASE)
    return m.group(1).upper() if m else os.path.splitext(filename)[0]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _base_result(referral_id: str, filename: str) -> Dict:
    return {
        "referral_id": referral_id,
        "source_file": filename,
        "synthetic": True,
        "extractor_version": __version__,
        "extraction_method": "none",
        "extraction_status": "FILE_UNREADABLE",
        "is_referral": None,
        "extraction": dict(_EMPTY_EXTRACTION),
        "missing_fields": None,
        "confidence": "n/a",
        "confidence_score": None,
        "confidence_reasons": [],
        "extraction_signals": {
            "urgent_red_flag": False,
            "suspected_cancer": False,
            "safeguarding": False,
            "child_patient": None,
        },
        "read_error": None,
        "extracted_at": _now(),
    }


def extract_referral(path: str) -> Dict:
    """Run the full pipeline for one referral file and return a validated result."""
    filename = os.path.basename(path)
    referral_id = _referral_id(filename)

    # 1. Read -------------------------------------------------------------
    try:
        text = read_referral_text(path)
    except FileUnreadableError as exc:
        result = _base_result(referral_id, filename)
        result["read_error"] = str(exc)
        result["confidence_reasons"] = ["file could not be read/parsed"]
        _validate_or_raise(result)
        return result

    return extract_referral_text(filename, text)


def extract_referral_text(source_file: str, text: str) -> Dict:
    """Pipeline for already-read text (used by the HTTP endpoint and tests)."""
    referral_id = _referral_id(os.path.basename(source_file))
    result = _base_result(referral_id, os.path.basename(source_file))

    if not text or not text.strip():
        result["read_error"] = "empty document text"
        result["confidence_reasons"] = ["file could not be read/parsed"]
        _validate_or_raise(result)
        return result

    # 2. Classify ---------------------------------------------------------
    is_referral = rx.classify_is_referral(text)
    result["is_referral"] = is_referral

    # 3. Extract ----------------------------------------------------------
    method = "regex"
    extraction = rx.extract_fields(text)
    if is_referral and llm_enabled():
        try:
            extraction = extract_fields_llm(text)
            method = "llm"
        except LLMUnavailable:
            extraction = rx.extract_fields(text)
            method = "llm+regex-fallback"
    result["extraction_method"] = method
    result["extraction"] = extraction

    # 4. Completeness + confidence + signals ------------------------------
    result["missing_fields"] = conf.compute_missing_fields(extraction)
    category, score, reasons = conf.compute_confidence(text, extraction, is_referral)
    result["confidence"] = category
    result["confidence_score"] = score
    result["confidence_reasons"] = reasons
    result["extraction_signals"] = conf.detect_signals(text, extraction)
    result["extraction_status"] = "OK" if is_referral else "NOT_A_REFERRAL"

    # 5. Validate ---------------------------------------------------------
    _validate_or_raise(result)
    return result


def _validate_or_raise(result: Dict) -> None:
    ok, errors = validate_result(result)
    if not ok:
        raise ValueError(
            f"Extraction result for {result.get('referral_id')} failed schema validation:\n  "
            + "\n  ".join(errors)
        )
