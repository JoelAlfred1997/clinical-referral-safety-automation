#!/usr/bin/env python3
"""Register an OpenMRS 3 (O3) 'Referral Form' so a human can enter a referral by
clicking, instead of via REST.

The form is bound to the SAME referral concepts the bot writes to, so a
manually-filled form produces an identical Referral encounter (and is picked up
by the duplicate check). This is the optional 'nicer clinical UI' noted in
openmrs-setup/seed-data/forms-config-notes.md.

What it does (idempotent):
  1. builds an O3 form-engine JSON schema from config/referral-metadata.json;
  2. creates a published Form of encounter type 'Referral';
  3. uploads the schema as clobdata and attaches it as the form's JSON resource.

Usage:  python setup_referral_form.py     (needs OpenMRS running + metadata setup)

ALL DATA IS SYNTHETIC.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
import uuid as uuidlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.metadata import load_metadata  # noqa: E402
from src.openmrs_client import OpenmrsClient  # noqa: E402

FORM_NAME = "Referral Form"
FORM_VERSION = "1.0"


def build_schema(metadata: dict) -> dict:
    c = metadata["concepts"]

    def q(label, concept_key, rendering="text"):
        return {
            "label": label,
            "id": concept_key,
            "type": "obs",
            "questionOptions": {"rendering": rendering, "concept": c[concept_key]},
        }

    return {
        "name": FORM_NAME,
        "version": FORM_VERSION,
        "description": "Synthetic inbound referral (NHS Referral Safety Automation).",
        "encounterType": metadata["encounter_type_uuid"],
        "processor": "EncounterFormProcessor",
        "referencedForms": [],
        "pages": [
            {
                "label": "Referral",
                "sections": [
                    {
                        "label": "Referral details",
                        "isExpanded": "true",
                        "questions": [
                            q("Speciality / department", "speciality"),
                            q("Urgency (Routine / Urgent / 2WW)", "urgency"),
                            q("Reason for referral", "reason", rendering="textarea"),
                            q("Referring clinician", "referrer_name"),
                            q("Referring GP practice", "referrer_org"),
                            q("Status (type: active)", "status"),
                            q("Letter reference (e.g. REF-001)", "source_id"),
                        ],
                    }
                ],
            }
        ],
    }


def _find_form(client: OpenmrsClient):
    data = client.get(f"/form?q={client.q(FORM_NAME)}&v=full")
    for r in data.get("results", []):
        if r.get("name") == FORM_NAME:
            return r
    return None


def _upload_clobdata(client: OpenmrsClient, schema: dict) -> str:
    """POST the schema as multipart clobdata; return its uuid."""
    boundary = "----referralform" + uuidlib.uuid4().hex
    payload = json.dumps(schema, ensure_ascii=False).encode("utf-8")
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="referral_form.json"\r\n'
        "Content-Type: application/json\r\n\r\n"
    ).encode("utf-8") + payload + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        f"{client.rest}/clobdata", data=body, method="POST",
    )
    req.add_header("Authorization", client._auth)  # reuse the client's Basic auth
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    with urllib.request.urlopen(req, timeout=40) as resp:
        text = resp.read().decode().strip().strip('"')
    return text


def main() -> int:
    client = OpenmrsClient()
    if not client.session_authenticated():
        print(f"OpenMRS not ready / not authenticated at {client.rest}.")
        return 1
    metadata = load_metadata()
    schema = build_schema(metadata)

    existing = _find_form(client)
    if existing:
        form_uuid = existing["uuid"]
        print(f"Form '{FORM_NAME}' already exists: {form_uuid} (will refresh its schema).")
    else:
        created = client.post("/form", {
            "name": FORM_NAME,
            "version": FORM_VERSION,
            "encounterType": metadata["encounter_type_uuid"],
            "description": "Synthetic inbound referral form.",
            "published": True,
        })
        form_uuid = created["uuid"]
        print(f"Created form '{FORM_NAME}': {form_uuid}")

    # Make sure it is published.
    client.post(f"/form/{form_uuid}", {"published": True})

    clob_uuid = _upload_clobdata(client, schema)
    print(f"Uploaded schema (clobdata): {clob_uuid}")

    client.post(f"/form/{form_uuid}/resource", {
        "name": "JSON schema",
        "dataType": "AmpathJsonSchema",
        "valueReference": clob_uuid,
    })
    print("Attached schema resource 'JSON schema'.")

    print(f"\nDone. Refresh the OpenMRS chart -> Start a visit -> Clinical forms -> '{FORM_NAME}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
