"""Schema validation for decision results.

Uses ``jsonschema`` (Draft-07) when available; falls back to a minimal built-in
check so the engine still runs in a bare Python environment. The fallback only
covers the shape the pipeline actually depends on, not the whole spec. (Same
pattern as the extraction service's validator.)
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Tuple

_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "schema", "decision.schema.json")

_MATCH_RESULTS = {
    "EXACT_MATCH", "DOB_MISMATCH", "PARTIAL_MATCH",
    "MULTIPLE_CANDIDATES", "NO_MATCH", "NOT_APPLICABLE",
}
_BOT_DECISIONS = {
    "AUTO_CREATE_REFERRAL_RECORD", "HUMAN_REVIEW_REQUIRED",
    "BUSINESS_EXCEPTION", "SYSTEM_EXCEPTION",
}
_FINAL_STATUSES = {
    "REFERRAL_CREATED_IN_OPENMRS", "ROUTED_TO_HUMAN_REVIEW",
    "BUSINESS_EXCEPTION_FAILED", "SYSTEM_EXCEPTION_ESCALATED",
}


def load_schema() -> Dict[str, Any]:
    with open(os.path.abspath(_SCHEMA_PATH), "r", encoding="utf-8") as fh:
        return json.load(fh)


def validate_decision(result: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Return (is_valid, errors). Never raises on validation failure."""
    schema = load_schema()
    try:
        import jsonschema  # type: ignore

        validator = jsonschema.Draft7Validator(schema)
        errors = [
            f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
            for e in sorted(validator.iter_errors(result), key=lambda e: list(e.absolute_path))
        ]
        return (len(errors) == 0, errors)
    except ImportError:
        return _minimal_validate(result, schema)


def _minimal_validate(result: Dict[str, Any], schema: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    for key in schema.get("required", []):
        if key not in result:
            errors.append(f"<root>: missing required key '{key}'")

    if result.get("synthetic") is not True:
        errors.append("synthetic: must be true")
    if result.get("match_result") not in _MATCH_RESULTS:
        errors.append(f"match_result: invalid value {result.get('match_result')!r}")
    if result.get("bot_decision") not in _BOT_DECISIONS:
        errors.append(f"bot_decision: invalid value {result.get('bot_decision')!r}")
    if result.get("final_status") not in _FINAL_STATUSES:
        errors.append(f"final_status: invalid value {result.get('final_status')!r}")

    reasons = result.get("reason_codes")
    if not isinstance(reasons, list) or len(reasons) < 1:
        errors.append("reason_codes: must be a non-empty array (every decision needs a reason)")

    if not isinstance(result.get("safety_flags"), list):
        errors.append("safety_flags: must be an array")

    return (len(errors) == 0, errors)
