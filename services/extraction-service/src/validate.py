"""Schema validation for extraction results.

Uses `jsonschema` when available (Draft-07). Falls back to a minimal built-in
check so the service still runs in a bare Python environment. The fallback only
covers the shape we actually depend on, not the whole spec.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Tuple

_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "schema", "extraction.schema.json")


def load_schema() -> Dict[str, Any]:
    with open(os.path.abspath(_SCHEMA_PATH), "r", encoding="utf-8") as fh:
        return json.load(fh)


def validate_result(result: Dict[str, Any]) -> Tuple[bool, List[str]]:
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
    """Tiny dependency-free subset: required top-level keys + a few enums."""
    errors: List[str] = []
    for key in schema.get("required", []):
        if key not in result:
            errors.append(f"<root>: missing required key '{key}'")

    if result.get("synthetic") is not True:
        errors.append("synthetic: must be true")

    if result.get("confidence") not in {"high", "medium", "low", "n/a"}:
        errors.append(f"confidence: invalid value {result.get('confidence')!r}")

    if result.get("extraction_status") not in {"OK", "NOT_A_REFERRAL", "FILE_UNREADABLE"}:
        errors.append(f"extraction_status: invalid value {result.get('extraction_status')!r}")

    extraction = result.get("extraction")
    if not isinstance(extraction, dict):
        errors.append("extraction: must be an object")
    else:
        nhs = extraction.get("patient_nhs_number")
        if nhs is not None and not (isinstance(nhs, str) and len(nhs) == 10 and nhs.isdigit()):
            errors.append("extraction/patient_nhs_number: must be 10 digits or null")
        gender = extraction.get("patient_gender")
        if gender not in {"M", "F", None}:
            errors.append("extraction/patient_gender: must be M, F or null")
        priority = extraction.get("priority")
        if priority not in {"Routine", "Urgent", "2WW", None}:
            errors.append("extraction/priority: must be Routine, Urgent, 2WW or null")

    return (len(errors) == 0, errors)
