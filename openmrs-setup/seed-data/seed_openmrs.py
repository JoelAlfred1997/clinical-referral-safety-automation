"""
seed_openmrs.py  —  Phase 2: load synthetic patients into OpenMRS via REST.

- Ensures a 'Synthetic NHS Number' patient identifier type exists.
- Creates each patient (with seed_to_openmrs=True) that is not already present.
- IDEMPOTENT: re-running does not create duplicates (it checks by NHS number first).
- Verifies the result with a couple of searches.

ALL DATA IS SYNTHETIC. Stdlib only (urllib).

Env overrides (defaults shown):
  OPENMRS_REST_URL  = http://localhost/openmrs/ws/rest/v1
  OPENMRS_USERNAME  = admin
  OPENMRS_PASSWORD  = Admin123

Run:  python seed_openmrs.py
"""
from __future__ import annotations
import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_FILE = REPO_ROOT / "data" / "synthetic-patients" / "synthetic_patients.json"

REST = os.environ.get("OPENMRS_REST_URL", "http://localhost/openmrs/ws/rest/v1").rstrip("/")
USER = os.environ.get("OPENMRS_USERNAME", "admin")
PWD = os.environ.get("OPENMRS_PASSWORD", "Admin123")

# Discovered in Phase 2 setup:
LOCATION_UUID = "44c3efb0-2583-4c80-a79e-1f756a03c0a1"          # Outpatient Clinic
PHONE_ATTR_UUID = "14d4f066-15f5-102d-96e4-000c29c2a5d7"        # Telephone Number
OPENMRS_ID_TYPE_UUID = "05a29f94-c0ed-11e2-94be-8c13b969e334"   # OpenMRS ID (required primary)
IDGEN_SOURCE_UUID = "8549f706-7e85-4c1d-9424-217d50a2988b"      # Generator for OpenMRS ID
NHS_ID_TYPE_NAME = "Synthetic NHS Number"

_AUTH = "Basic " + base64.b64encode(f"{USER}:{PWD}".encode()).decode()


def _req(method: str, path: str, body: dict | None = None):
    url = path if path.startswith("http") else f"{REST}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", _AUTH)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode()[:500]}


def ensure_nhs_identifier_type() -> str:
    status, data = _req("GET", "/patientidentifiertype?v=default&limit=100")
    for t in data.get("results", []):
        if t.get("display") == NHS_ID_TYPE_NAME:
            print(f"Identifier type '{NHS_ID_TYPE_NAME}' already exists: {t['uuid']}")
            return t["uuid"]
    body = {
        "name": NHS_ID_TYPE_NAME,
        "description": "SYNTHETIC NHS-style number (999 test range, valid Mod-11). Not a real NHS number.",
        "required": False,
    }
    status, data = _req("POST", "/patientidentifiertype", body)
    if status not in (200, 201):
        raise SystemExit(f"Failed to create identifier type ({status}): {data}")
    print(f"Created identifier type '{NHS_ID_TYPE_NAME}': {data['uuid']}")
    return data["uuid"]


def patient_exists(nhs_number: str) -> bool:
    status, data = _req("GET", f"/patient?q={nhs_number}&v=default&limit=5")
    for r in data.get("results", []):
        if nhs_number in (r.get("display") or ""):
            return True
        # be robust: check identifiers explicitly
        st2, full = _req("GET", f"/patient/{r['uuid']}?v=full")
        for ident in full.get("identifiers", []):
            if ident.get("identifier") == nhs_number:
                return True
    return False


def generate_openmrs_id() -> str:
    """Generate a new OpenMRS ID from the idgen identifier source (required primary id)."""
    status, data = _req("POST", f"/idgen/identifiersource/{IDGEN_SOURCE_UUID}/identifier", {})
    if status not in (200, 201) or not data.get("identifier"):
        raise SystemExit(f"Failed to generate OpenMRS ID ({status}): {data}")
    return data["identifier"]


def create_patient(p: dict, nhs_type_uuid: str):
    openmrs_id = generate_openmrs_id()
    body = {
        "person": {
            "names": [{"givenName": p["first_name"], "familyName": p["last_name"]}],
            "gender": p["gender"],
            "birthdate": p["date_of_birth"],
            "addresses": [{
                "postalCode": p["postcode"],
                "country": "United Kingdom",
            }],
            "attributes": [
                {"attributeType": PHONE_ATTR_UUID, "value": p["phone"]},
            ],
        },
        "identifiers": [
            {   # required primary identifier
                "identifier": openmrs_id,
                "identifierType": OPENMRS_ID_TYPE_UUID,
                "location": LOCATION_UUID,
                "preferred": True,
            },
            {   # our synthetic NHS-style identifier (searchable, used for matching)
                "identifier": p["nhs_number"],
                "identifierType": nhs_type_uuid,
                "location": LOCATION_UUID,
                "preferred": False,
            },
        ],
    }
    return _req("POST", "/patient", body)


def main() -> None:
    if not DATA_FILE.exists():
        raise SystemExit(f"Dataset not found: {DATA_FILE}\nRun generate_patients.py first.")
    patients = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    print(f"OpenMRS REST: {REST}  (user={USER})")
    nhs_type_uuid = ensure_nhs_identifier_type()

    created = skipped = failed = reserved = 0
    for p in patients:
        if not p["seed_to_openmrs"]:
            reserved += 1
            print(f"  RESERVED (no-match, not loaded): {p['synthetic_id']} {p['first_name']} {p['last_name']} [{p['nhs_number']}]")
            continue
        if patient_exists(p["nhs_number"]):
            skipped += 1
            print(f"  SKIP exists: {p['synthetic_id']} {p['first_name']} {p['last_name']} [{p['nhs_number']}]")
            continue
        status, data = create_patient(p, nhs_type_uuid)
        if status in (200, 201) and data.get("uuid"):
            created += 1
            print(f"  CREATED: {p['synthetic_id']} {p['first_name']} {p['last_name']} [{p['nhs_number']}] -> {data['uuid']}")
        else:
            failed += 1
            print(f"  FAIL ({status}): {p['synthetic_id']} {p['first_name']} {p['last_name']} -> {data}")

    print(f"\nSummary: created={created}, skipped(existing)={skipped}, "
          f"reserved(no-match)={reserved}, failed={failed}")

    # Verify
    print("\nVerification:")
    for nhs in [patients[0]["nhs_number"]]:
        st, d = _req("GET", f"/patient?q={nhs}&v=default")
        print(f"  search by NHS {nhs}: {len(d.get('results', []))} result(s)")
    st, d = _req("GET", "/patient?q=Walsh&v=default")
    print(f"  search 'Walsh' (multiple_candidate): {len(d.get('results', []))} result(s)")


if __name__ == "__main__":
    main()
