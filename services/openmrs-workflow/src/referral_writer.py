"""The concrete OpenMRS referral write/read path (no log-message-only steps).

A referral is modelled with the native OpenMRS clinical data model — one
`Referral` **Encounter** carrying one **Observation** per referral field — so it
is fully reachable and verifiable over REST.

Key behaviours:
  * ``create_referral`` writes the encounter + obs and returns the new uuid.
  * ``verify_referral`` re-reads the encounter and confirms every field round-trips
    (this is the "verify by re-read" the architecture requires for AUTO_CREATE).
  * ``get_referral_encounters`` / ``find_active_referrals`` read a patient's
    referrals back out — the live duplicate-referral check.
  * writes are **idempotent**: keyed on the source-document id observation
    (REF-NNN), so re-running never creates a second encounter for the same input.

ALL DATA IS SYNTHETIC.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from .openmrs_client import OpenmrsClient

# Encounter read projection: the obs we need, with concept uuid + value.
_ENCOUNTER_REP = (
    "custom:(uuid,encounterDatetime,voided,"
    "obs:(uuid,concept:(uuid,display),value))"
)


def _fmt_datetime(dt: datetime) -> str:
    # OpenMRS expects an ISO datetime with a timezone offset.
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000%z") or dt.strftime("%Y-%m-%dT%H:%M:%S.000+0000")


def _now_offset(days_ago: int = 0) -> str:
    dt = datetime.now().astimezone() - timedelta(days=days_ago)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000%z")


# The fields a referral encounter records, in obs order. Values are taken from
# the Phase 4 extraction; status/source_id are workflow fields.
REFERRAL_FIELD_KEYS = [
    "speciality", "urgency", "reason",
    "referrer_name", "referrer_org",
    "status", "source_id", "suspected_cancer",
]


def build_fields(extraction: Dict, source_id: str, status: str = "active",
                 suspected_cancer: Optional[bool] = None) -> Dict:
    """Map a Phase 4 extraction dict to the referral obs field values."""
    ex = extraction.get("extraction", extraction)
    return {
        "speciality": ex.get("specialty"),
        "urgency": ex.get("priority"),
        "reason": ex.get("reason_for_referral"),
        "referrer_name": ex.get("referring_clinician"),
        "referrer_org": ex.get("referring_practice"),
        "status": status,
        "source_id": source_id,
        "suspected_cancer": bool(
            (extraction.get("extraction_signals") or {}).get("suspected_cancer")
        ) if suspected_cancer is None else suspected_cancer,
    }


def _obs_payload(metadata: Dict, fields: Dict) -> List[Dict]:
    concepts = metadata["concepts"]
    obs: List[Dict] = []
    for key in REFERRAL_FIELD_KEYS:
        value = fields.get(key)
        if key == "suspected_cancer":
            # Only record the boolean obs when the signal is positive; a routine
            # referral simply omits it (avoids writing a False boolean obs).
            if value:
                obs.append({"concept": concepts[key], "value": True})
            continue
        if value is None or value == "":
            continue
        obs.append({"concept": concepts[key], "value": value})
    return obs


def create_referral(
    client: OpenmrsClient,
    metadata: Dict,
    patient_uuid: str,
    fields: Dict,
    encounter_datetime: Optional[str] = None,
) -> str:
    """Write a Referral encounter + observations; return the new encounter uuid."""
    body = {
        "patient": patient_uuid,
        "encounterType": metadata["encounter_type_uuid"],
        "location": metadata["location_uuid"],
        "encounterDatetime": encounter_datetime or _now_offset(),
        "obs": _obs_payload(metadata, fields),
    }
    created = client.post("/encounter", body)
    return created["uuid"]


def _obs_to_fields(metadata: Dict, obs_list: List[Dict]) -> Dict:
    """Invert a read-back encounter's obs into our field keys."""
    uuid_to_key = {v: k for k, v in metadata["concepts"].items()}
    out: Dict = {}
    for ob in obs_list:
        cuuid = (ob.get("concept") or {}).get("uuid")
        key = uuid_to_key.get(cuuid)
        if key:
            out[key] = ob.get("value")
    return out


def get_referral_encounters(client: OpenmrsClient, metadata: Dict, patient_uuid: str) -> List[Dict]:
    """All non-voided Referral encounters for a patient, with decoded fields."""
    etype = metadata["encounter_type_uuid"]
    data = client.get(
        f"/encounter?patient={patient_uuid}&encounterType={etype}"
        f"&v={_ENCOUNTER_REP}&limit=100"
    )
    encounters = []
    for enc in data.get("results", []):
        if enc.get("voided"):
            continue
        fields = _obs_to_fields(metadata, enc.get("obs", []))
        encounters.append({
            "uuid": enc["uuid"],
            "encounterDatetime": enc.get("encounterDatetime"),
            "fields": fields,
        })
    return encounters


def find_by_source_id(client: OpenmrsClient, metadata: Dict, patient_uuid: str,
                      source_id: str) -> Optional[Dict]:
    """Idempotency lookup: an existing referral encounter for this REF-NNN."""
    for enc in get_referral_encounters(client, metadata, patient_uuid):
        if enc["fields"].get("source_id") == source_id:
            return enc
    return None


def find_active_referrals(client: OpenmrsClient, metadata: Dict, patient_uuid: str) -> List[Dict]:
    """The live duplicate-referral signal: active referrals with their speciality."""
    out = []
    for enc in get_referral_encounters(client, metadata, patient_uuid):
        f = enc["fields"]
        if (f.get("status") or "").lower() == "active" and f.get("speciality"):
            out.append({
                "uuid": enc["uuid"],
                "speciality": f.get("speciality"),
                "source_id": f.get("source_id"),
            })
    return out


def existing_referral_status(client: OpenmrsClient, metadata: Dict, patient_uuid: str) -> str:
    """'active:<Speciality>' for the first active referral, else 'none'.

    This is the live equivalent of the seed file's existing_referral_status that
    the Phase 5 decision engine consumes.
    """
    active = find_active_referrals(client, metadata, patient_uuid)
    return f"active:{active[0]['speciality']}" if active else "none"


def verify_referral(client: OpenmrsClient, metadata: Dict, encounter_uuid: str,
                    expected: Dict) -> Tuple[bool, List[str]]:
    """Re-read the encounter and confirm each expected field round-trips."""
    enc = client.get(f"/encounter/{encounter_uuid}?v={_ENCOUNTER_REP}")
    got = _obs_to_fields(metadata, enc.get("obs", []))
    mismatches = []
    for key in REFERRAL_FIELD_KEYS:
        exp = expected.get(key)
        if exp is None or exp == "":
            continue
        if key == "suspected_cancer":
            if bool(got.get(key)) != bool(exp):
                mismatches.append(f"{key}: got {got.get(key)!r} exp {bool(exp)!r}")
        elif (got.get(key) or "") != exp:
            mismatches.append(f"{key}: got {got.get(key)!r} exp {exp!r}")
    return (not mismatches, mismatches)


def write_referral_idempotent(
    client: OpenmrsClient,
    metadata: Dict,
    patient_uuid: str,
    fields: Dict,
    encounter_datetime: Optional[str] = None,
) -> Tuple[str, str]:
    """Create the referral unless one with the same source_id already exists.

    Returns (encounter_uuid, action) where action is 'created' or 'exists'.
    """
    source_id = fields.get("source_id")
    if source_id:
        existing = find_by_source_id(client, metadata, patient_uuid, source_id)
        if existing:
            return existing["uuid"], "exists"
    uuid = create_referral(client, metadata, patient_uuid, fields, encounter_datetime)
    return uuid, "created"
