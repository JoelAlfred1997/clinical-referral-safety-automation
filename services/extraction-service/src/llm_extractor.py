"""Optional LLM extraction path (Groq / OpenAI-compatible chat completions).

Deliberately narrow scope: the model is asked ONLY to return the structured
referral fields as JSON. It has zero authority over matching, routing, or any
clinical decision. Its output is parsed, coerced through the SAME normalisers
and the SAME schema validation as the regex path, and if anything fails we fall
back to regex. This is the "AI-assisted, deterministically-guarded" design the
project is built to demonstrate.

Enabled only when USE_LLM=true AND an API key is configured. Otherwise the
orchestrator never calls this module.
"""

from __future__ import annotations

import json
import os
from typing import Dict, Optional

from . import regex_extractor as rx

_SYSTEM_PROMPT = (
    "You extract fields from a UK NHS GP referral letter. The data is SYNTHETIC "
    "test data. Return ONLY a JSON object, no prose. Use exactly these keys: "
    "patient_nhs_number, patient_first_name, patient_last_name, patient_dob, "
    "patient_gender, referral_date, referring_clinician, referring_practice, "
    "specialty, priority, reason_for_referral. "
    "Rules: NHS number as 10 digits with no spaces, or null. Dates as YYYY-MM-DD. "
    "Gender as 'M' or 'F'. priority as one of 'Routine','Urgent','2WW' (2WW = "
    "2-week-wait / suspected cancer) or null. reason_for_referral: a concise "
    "one-sentence clinical summary. Use null for anything not present. Do NOT "
    "guess an NHS number or invent values."
)

_FIELDS = [
    "patient_nhs_number", "patient_first_name", "patient_last_name", "patient_dob",
    "patient_gender", "referral_date", "referring_clinician", "referring_practice",
    "specialty", "priority", "reason_for_referral",
]


class LLMUnavailable(Exception):
    """Raised when the LLM cannot be used (disabled, no key, or call failed)."""


def llm_enabled() -> bool:
    if os.getenv("USE_LLM", "false").strip().lower() not in {"1", "true", "yes"}:
        return False
    return bool(_api_key())


def _api_key() -> Optional[str]:
    provider = os.getenv("LLM_PROVIDER", "groq").strip().lower()
    key_var = {"groq": "GROQ_API_KEY", "openai": "OPENAI_API_KEY"}.get(provider, "GROQ_API_KEY")
    key = os.getenv(key_var, "").strip()
    return key or None


def extract_fields_llm(text: str) -> Dict[str, Optional[str]]:
    """Call the configured chat-completions endpoint and coerce the response.

    Raises LLMUnavailable on any problem so the caller can fall back to regex.
    """
    if not llm_enabled():
        raise LLMUnavailable("LLM disabled or no API key configured")

    try:
        import requests  # type: ignore
    except ImportError as exc:
        raise LLMUnavailable("requests not installed") from exc

    endpoint = os.getenv(
        "GROQ_ENDPOINT", "https://api.groq.com/openai/v1/chat/completions"
    )
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))

    payload = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
    }
    headers = {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(endpoint, json=payload, headers=headers, timeout=timeout)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        data = json.loads(content)
    except Exception as exc:  # network, auth, malformed JSON -- all -> fallback
        raise LLMUnavailable(f"LLM call/parse failed: {exc}") from exc

    if not isinstance(data, dict):
        raise LLMUnavailable("LLM did not return a JSON object")

    return _coerce(data)


def _coerce(data: Dict[str, object]) -> Dict[str, Optional[str]]:
    """Push raw LLM values through the deterministic normalisers/whitelists."""
    def s(key: str) -> Optional[str]:
        val = data.get(key)
        if val is None:
            return None
        val = str(val).strip()
        return val or None

    return {
        "patient_nhs_number": rx._normalise_nhs(s("patient_nhs_number")),
        "patient_first_name": s("patient_first_name"),
        "patient_last_name": s("patient_last_name"),
        "patient_dob": rx._normalise_date(s("patient_dob")) or s("patient_dob"),
        "patient_gender": rx._normalise_gender(s("patient_gender")),
        "referral_date": rx._normalise_date(s("referral_date")) or s("referral_date"),
        "referring_clinician": s("referring_clinician"),
        "referring_practice": s("referring_practice"),
        "specialty": s("specialty"),
        "priority": rx.normalise_priority(s("priority")),
        "reason_for_referral": s("reason_for_referral"),
    }
