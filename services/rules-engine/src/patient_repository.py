"""Patient lookup against a repository of patients.

Two interchangeable backends behind one interface:

  * ``LocalPatientRepository`` -- reads the committed synthetic-patient seed file
    (``data/synthetic-patients/synthetic_patients.json``). Only patients with
    ``seed_to_openmrs == True`` are considered "in OpenMRS"; the reserved
    no-match fixtures are deliberately excluded. It also surfaces each patient's
    ``existing_referral_status`` so the duplicate-referral check is testable
    OFFLINE and DETERMINISTICALLY. This is the backend the Phase 5 acceptance
    gate uses -- no Docker, no network, fully reproducible (the same philosophy
    as the Phase 4 regex guardrail path).

  * ``OpenmrsPatientRepository`` -- queries a live OpenMRS instance over REST
    (stdlib only). This is the production path the UiPath performer uses in
    Phase 8. Demographic search + identifier lookup mirror the Phase 2 seeder.

Both return the same normalised patient dict shape:

    {
        "nhs_number": str | None,
        "first_name": str | None,
        "last_name": str | None,
        "date_of_birth": str | None,   # YYYY-MM-DD
        "gender": str | None,          # M / F
        "existing_referral_status": str | None,   # "none" | "active:<Specialty>"
        "source": "local-seed" | "openmrs",
    }

ALL DATA IS SYNTHETIC.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SEED_FILE = _REPO_ROOT / "data" / "synthetic-patients" / "synthetic_patients.json"


def _normalise(raw: Dict, source: str) -> Dict:
    return {
        "nhs_number": raw.get("nhs_number"),
        "first_name": raw.get("first_name"),
        "last_name": raw.get("last_name"),
        "date_of_birth": raw.get("date_of_birth"),
        "gender": raw.get("gender"),
        "existing_referral_status": raw.get("existing_referral_status", "none"),
        "source": source,
    }


class LocalPatientRepository:
    """Patient lookup against the synthetic-patient seed file (offline, deterministic).

    Mirrors what OpenMRS actually contains after the Phase 2 seeder runs: a
    patient is "present" iff ``seed_to_openmrs`` is True. The reserved no-match
    fixtures (Fernandes, Osei) are excluded, so they correctly return NO_MATCH.
    """

    source = "local-seed"

    def __init__(self, seed_path: Optional[Path] = None):
        path = Path(seed_path) if seed_path else _SEED_FILE
        if not path.exists():
            raise FileNotFoundError(
                f"Synthetic patient seed file not found: {path}\n"
                "Run openmrs-setup/seed-data/generate_patients.py first."
            )
        records = json.loads(path.read_text(encoding="utf-8"))
        # Only patients actually loaded into OpenMRS are matchable.
        self._patients: List[Dict] = [
            _normalise(p, self.source) for p in records if p.get("seed_to_openmrs")
        ]

    def find_by_nhs_number(self, nhs_number: str) -> Optional[Dict]:
        for p in self._patients:
            if p["nhs_number"] == nhs_number:
                return p
        return None

    def find_by_demographics(
        self, first_name: Optional[str], last_name: Optional[str], dob: Optional[str]
    ) -> List[Dict]:
        if not (first_name and last_name and dob):
            return []
        f, l = first_name.strip().lower(), last_name.strip().lower()
        return [
            p
            for p in self._patients
            if (p["first_name"] or "").strip().lower() == f
            and (p["last_name"] or "").strip().lower() == l
            and p["date_of_birth"] == dob
        ]


class OpenmrsPatientRepository:
    """Patient lookup against a live OpenMRS instance over REST (Phase 8 path).

    Stdlib only (urllib), same auth/host conventions as the Phase 2 seeder.

    NOTE on duplicate detection: ``existing_referral_status`` requires the
    'Referral' encounter type/concepts, which are created in Phase 6. Until then
    this backend reports "none" (the duplicate check is inert against live
    OpenMRS), while the local-seed backend carries the status so the duplicate
    scenario (REF-007) is still exercised by the Phase 5 gate. This is the
    documented dependency in data/expected-outcomes/README.md.
    """

    source = "openmrs"

    def __init__(
        self,
        rest_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.rest = (rest_url or os.environ.get(
            "OPENMRS_REST_URL", "http://localhost/openmrs/ws/rest/v1"
        )).rstrip("/")
        user = username or os.environ.get("OPENMRS_USERNAME", "admin")
        pwd = password or os.environ.get("OPENMRS_PASSWORD", "Admin123")
        self._auth = "Basic " + base64.b64encode(f"{user}:{pwd}".encode()).decode()

    def _get(self, path: str):
        url = path if path.startswith("http") else f"{self.rest}{path}"
        req = urllib.request.Request(url, method="GET")
        req.add_header("Authorization", self._auth)
        req.add_header("Accept", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:
                raw = resp.read().decode()
                return resp.status, (json.loads(raw) if raw else {})
        except urllib.error.HTTPError as e:
            return e.code, {"error": e.read().decode()[:500]}

    def _patient_to_dict(self, full: Dict) -> Dict:
        person = full.get("person", {})
        name = (person.get("preferredName") or {})
        nhs_number = None
        for ident in full.get("identifiers", []):
            itype = (ident.get("identifierType") or {}).get("display", "")
            if "NHS" in itype:
                nhs_number = ident.get("identifier")
        return _normalise(
            {
                "nhs_number": nhs_number,
                "first_name": name.get("givenName"),
                "last_name": name.get("familyName"),
                "date_of_birth": (person.get("birthdate") or "")[:10] or None,
                "gender": person.get("gender"),
                "existing_referral_status": "none",  # see class docstring
            },
            self.source,
        )

    def _search(self, query: str) -> List[Dict]:
        status, data = self._get(f"/patient?q={urllib.parse.quote(query)}&v=full&limit=20")
        if status != 200:
            return []
        return [self._patient_to_dict(r) for r in data.get("results", [])]

    def find_by_nhs_number(self, nhs_number: str) -> Optional[Dict]:
        for p in self._search(nhs_number):
            if p["nhs_number"] == nhs_number:
                return p
        return None

    def find_by_demographics(
        self, first_name: Optional[str], last_name: Optional[str], dob: Optional[str]
    ) -> List[Dict]:
        if not (first_name and last_name and dob):
            return []
        f, l = first_name.strip().lower(), last_name.strip().lower()
        return [
            p
            for p in self._search(last_name)
            if (p["first_name"] or "").strip().lower() == f
            and (p["last_name"] or "").strip().lower() == l
            and p["date_of_birth"] == dob
        ]


# urllib.parse is only needed by the OpenMRS backend; import lazily-safe here.
import urllib.parse  # noqa: E402


def get_patient_repository(source: str = "local"):
    """Factory. ``source`` is 'local' (seed file, default) or 'openmrs' (live REST)."""
    source = (source or "local").lower()
    if source in ("local", "local-seed", "seed"):
        return LocalPatientRepository()
    if source in ("openmrs", "rest"):
        return OpenmrsPatientRepository()
    raise ValueError(f"Unknown patient repository source: {source!r}")
