#!/usr/bin/env python3
"""Phase 6 setup: ensure the Referral encounter type + referral concepts exist.

Idempotent — re-running re-uses existing metadata and never duplicates it. The
resolved UUIDs are cached to config/referral-metadata.json for the writer/bot.

Usage:
    python setup_referral_metadata.py

Needs OpenMRS running (docker compose -f openmrs-setup/docker-compose.yml up -d).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.metadata import ensure_referral_metadata  # noqa: E402
from src.openmrs_client import OpenmrsClient  # noqa: E402


def main() -> int:
    client = OpenmrsClient()
    if not client.session_authenticated():
        print(f"OpenMRS not ready / not authenticated at {client.rest}.")
        print("Start it: docker compose -f openmrs-setup/docker-compose.yml up -d")
        return 1

    print(f"OpenMRS REST: {client.rest}")
    metadata = ensure_referral_metadata(client, save=True)

    print(f"Encounter type 'Referral': {metadata['encounter_type_uuid']}")
    print(f"Location:                  {metadata['location_uuid']}")
    print(f"Concept class:             {metadata['concept_class_uuid']}")
    print("Concepts:")
    for key, uuid in metadata["concepts"].items():
        print(f"  {key:<18} {metadata['concept_names'][key]:<34} {uuid}")
    print("\nSaved -> config/referral-metadata.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
