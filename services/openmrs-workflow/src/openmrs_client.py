"""Thin OpenMRS REST client (stdlib only).

Same host/auth conventions as the Phase 2 seeder (openmrs-setup/seed-data/
seed_openmrs.py): HTTP Basic auth, JSON in/out, configurable via environment.
No third-party HTTP dependency — the bot and the setup scripts share this client.

ALL DATA IS SYNTHETIC.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Tuple


class OpenmrsError(RuntimeError):
    """Raised for an unexpected (non-2xx) OpenMRS REST response."""

    def __init__(self, status: int, detail: Any):
        super().__init__(f"OpenMRS REST error {status}: {detail}")
        self.status = status
        self.detail = detail


class OpenmrsClient:
    def __init__(
        self,
        rest_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 40,
    ):
        self.rest = (rest_url or os.environ.get(
            "OPENMRS_REST_URL", "http://localhost/openmrs/ws/rest/v1"
        )).rstrip("/")
        user = username or os.environ.get("OPENMRS_USERNAME", "admin")
        pwd = password or os.environ.get("OPENMRS_PASSWORD", "Admin123")
        self._auth = "Basic " + base64.b64encode(f"{user}:{pwd}".encode()).decode()
        self.timeout = timeout

    # -- low level --------------------------------------------------------
    def request(self, method: str, path: str, body: Optional[Dict] = None) -> Tuple[int, Dict]:
        url = path if path.startswith("http") else f"{self.rest}{path}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", self._auth)
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode()
                return resp.status, (json.loads(raw) if raw else {})
        except urllib.error.HTTPError as e:
            detail = e.read().decode()[:800]
            try:
                detail = json.loads(detail)
            except (ValueError, json.JSONDecodeError):
                pass
            return e.code, {"error": detail}

    def get(self, path: str) -> Dict:
        status, data = self.request("GET", path)
        if status != 200:
            raise OpenmrsError(status, data.get("error", data))
        return data

    def post(self, path: str, body: Dict) -> Dict:
        status, data = self.request("POST", path, body)
        if status not in (200, 201):
            raise OpenmrsError(status, data.get("error", data))
        return data

    # -- helpers ----------------------------------------------------------
    @staticmethod
    def q(value: str) -> str:
        return urllib.parse.quote(str(value))

    def session_authenticated(self) -> bool:
        """The Phase 1 readiness gate: REST /session returns authenticated:true."""
        try:
            status, data = self.request("GET", "/session")
        except urllib.error.URLError:
            return False
        return status == 200 and bool(data.get("authenticated"))

    def find_patient_by_nhs(self, nhs_number: str) -> Optional[Dict]:
        """Return the OpenMRS patient (v=full) whose Synthetic NHS Number == nhs_number."""
        data = self.get(f"/patient?q={self.q(nhs_number)}&v=full&limit=10")
        for r in data.get("results", []):
            for ident in r.get("identifiers", []):
                if ident.get("identifier") == nhs_number:
                    return r
        return None
