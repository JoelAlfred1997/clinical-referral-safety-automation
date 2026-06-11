"""Idempotent OpenMRS metadata setup for referrals.

Ensures the building blocks a referral record needs exist, creating them only if
absent and re-using them otherwise:

  * the `Referral` encounter type;
  * one obs **concept** per referral field (speciality, urgency, reason, referrer
    name/organisation, a status flag, the source-document id, suspected-cancer).

Concept datatype/class and the clinic location are **discovered** from the live
instance rather than hard-coded, so this works against any OpenMRS that has the
standard reference metadata. The resolved UUIDs are cached to
`config/referral-metadata.json` for the writer and the bot to read.

ALL DATA IS SYNTHETIC.
"""

from __future__ import annotations

import json
import os
from typing import Dict

from .openmrs_client import OpenmrsClient

_CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config")
_CONFIG_PATH = os.path.join(_CONFIG_DIR, "referral-metadata.json")

ENCOUNTER_TYPE_NAME = "Referral"
ENCOUNTER_TYPE_DESC = "Synthetic inbound referral record (NHS Referral Safety Automation)."

# Fallback discovered in Phase 2 if /location search returns nothing.
_FALLBACK_LOCATION_UUID = "44c3efb0-2583-4c80-a79e-1f756a03c0a1"  # Outpatient Clinic

# key -> (fully-specified concept name, datatype display)
REFERRAL_CONCEPTS = {
    "speciality": ("Referral - Speciality", "Text"),
    "urgency": ("Referral - Urgency", "Text"),
    "reason": ("Referral - Reason", "Text"),
    "referrer_name": ("Referral - Referrer Name", "Text"),
    "referrer_org": ("Referral - Referrer Organisation", "Text"),
    "status": ("Referral - Status", "Text"),
    "source_id": ("Referral - Source Document ID", "Text"),
    "suspected_cancer": ("Referral - Suspected Cancer", "Boolean"),
}


def _display_map(client: OpenmrsClient, resource: str) -> Dict[str, str]:
    """display -> uuid for a small reference resource (no q filter; fetch all)."""
    data = client.get(f"/{resource}?v=default&limit=100")
    return {r.get("display"): r["uuid"] for r in data.get("results", []) if r.get("display")}


def _discover_datatype_uuids(client: OpenmrsClient) -> Dict[str, str]:
    # /conceptdatatype does not support a 'q' filter, so fetch the full list.
    all_types = _display_map(client, "conceptdatatype")
    out: Dict[str, str] = {}
    for name in {dt for _, dt in REFERRAL_CONCEPTS.values()}:
        if name not in all_types:
            raise RuntimeError(f"Concept datatype '{name}' not found in OpenMRS.")
        out[name] = all_types[name]
    return out


def _discover_question_class(client: OpenmrsClient) -> str:
    classes = _display_map(client, "conceptclass")
    for name in ("Question", "Misc", "Finding"):
        if name in classes:
            return classes[name]
    raise RuntimeError("No suitable concept class (Question/Misc/Finding) found.")


def _discover_location(client: OpenmrsClient) -> str:
    for display, uuid in _display_map(client, "location").items():
        if "Outpatient" in display:
            return uuid
    return _FALLBACK_LOCATION_UUID


def _ensure_encounter_type(client: OpenmrsClient) -> str:
    data = client.get("/encountertype?q=Referral&v=default&limit=50")
    for r in data.get("results", []):
        if r.get("display") == ENCOUNTER_TYPE_NAME:
            return r["uuid"]
    created = client.post("/encountertype", {
        "name": ENCOUNTER_TYPE_NAME,
        "description": ENCOUNTER_TYPE_DESC,
    })
    return created["uuid"]


def _find_concept_by_name(client: OpenmrsClient, name: str) -> str | None:
    data = client.get(f"/concept?q={client.q(name)}&v=default&limit=50")
    for r in data.get("results", []):
        if (r.get("display") or "").strip() == name:
            return r["uuid"]
    return None


def _ensure_concept(client: OpenmrsClient, name: str, datatype_uuid: str, class_uuid: str) -> str:
    existing = _find_concept_by_name(client, name)
    if existing:
        return existing
    created = client.post("/concept", {
        "names": [{"name": name, "locale": "en", "conceptNameType": "FULLY_SPECIFIED"}],
        "datatype": datatype_uuid,
        "conceptClass": class_uuid,
    })
    return created["uuid"]


def ensure_referral_metadata(client: OpenmrsClient, save: bool = True) -> Dict:
    """Create/resolve all referral metadata and return the resolved UUID map."""
    datatypes = _discover_datatype_uuids(client)
    class_uuid = _discover_question_class(client)
    location_uuid = _discover_location(client)
    encounter_type_uuid = _ensure_encounter_type(client)

    concepts: Dict[str, str] = {}
    for key, (name, dt_name) in REFERRAL_CONCEPTS.items():
        concepts[key] = _ensure_concept(client, name, datatypes[dt_name], class_uuid)

    metadata = {
        "synthetic": True,
        "rest_url": client.rest,
        "encounter_type_uuid": encounter_type_uuid,
        "location_uuid": location_uuid,
        "concept_class_uuid": class_uuid,
        "datatype_uuids": datatypes,
        "concepts": concepts,
        "concept_names": {k: v[0] for k, v in REFERRAL_CONCEPTS.items()},
    }
    if save:
        os.makedirs(_CONFIG_DIR, exist_ok=True)
        with open(_CONFIG_PATH, "w", encoding="utf-8") as fh:
            json.dump(metadata, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
    return metadata


def load_metadata() -> Dict:
    if not os.path.exists(_CONFIG_PATH):
        raise FileNotFoundError(
            f"Referral metadata config not found: {_CONFIG_PATH}\n"
            "Run setup_referral_metadata.py first (needs OpenMRS running)."
        )
    with open(_CONFIG_PATH, encoding="utf-8") as fh:
        return json.load(fh)
