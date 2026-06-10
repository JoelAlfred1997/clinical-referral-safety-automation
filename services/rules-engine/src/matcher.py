"""Patient matching: extraction fields -> a single match outcome.

Implements architecture steps 6-7 (search patient, validate match). Pure logic
over a PatientRepository, so it is identical whether the repository is the
offline seed file or live OpenMRS.

Match precedence (deterministic, wrong-patient-safe):

  * NHS number supplied AND resolves to a patient
        - demographics (surname + DOB) agree -> EXACT_MATCH
        - demographics conflict             -> DOB_MISMATCH   (identifier vs
          demographic conflict = wrong-patient risk; never trusted)
  * NHS number absent, OR supplied but not found -> fall back to demographics
    (first + last + DOB):
        - 0 candidates -> NO_MATCH
        - 1 candidate  -> PARTIAL_MATCH   (probable but unverified identity)
        - >1 candidates-> MULTIPLE_CANDIDATES  (cannot safely disambiguate)

A supplied-but-unresolved NHS number never silently "becomes" a demographic
match: at best it is PARTIAL (unconfirmed identifier), so it always routes to a
human.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Match:
    match_result: str
    matched_patient: Optional[Dict] = None
    candidate_count: int = 0
    duplicate_active_referral: bool = False
    matched_specialty: Optional[str] = None  # the existing active referral's specialty, if any
    notes: List[str] = field(default_factory=list)


def _demographics_agree(patient: Dict, extraction: Dict) -> bool:
    """Surname + DOB agreement between a resolved patient and the referral."""
    surname_ok = (patient.get("last_name") or "").strip().lower() == (
        extraction.get("patient_last_name") or ""
    ).strip().lower()
    dob_ok = patient.get("date_of_birth") == extraction.get("patient_dob")
    return surname_ok and dob_ok


def _parse_active_specialty(existing_status: Optional[str]) -> Optional[str]:
    """'active:Cardiology' -> 'Cardiology'; anything else -> None."""
    if not existing_status or ":" not in existing_status:
        return None
    state, _, spec = existing_status.partition(":")
    return spec.strip() if state.strip().lower() == "active" and spec.strip() else None


def _duplicate(patient: Dict, extraction: Dict) -> tuple[bool, Optional[str]]:
    """Same patient + same speciality + an active existing referral = duplicate risk."""
    active_spec = _parse_active_specialty(patient.get("existing_referral_status"))
    if not active_spec:
        return False, None
    referral_spec = (extraction.get("specialty") or "").strip().lower()
    is_dup = bool(referral_spec) and referral_spec == active_spec.strip().lower()
    return is_dup, active_spec


def match_patient(extraction: Dict, repo) -> Match:
    """Resolve the referral's patient against ``repo`` and classify the match."""
    nhs = extraction.get("patient_nhs_number")
    first = extraction.get("patient_first_name")
    last = extraction.get("patient_last_name")
    dob = extraction.get("patient_dob")

    # --- Identifier-first ------------------------------------------------
    if nhs:
        patient = repo.find_by_nhs_number(nhs)
        if patient:
            is_dup, active_spec = _duplicate(patient, extraction)
            if _demographics_agree(patient, extraction):
                return Match(
                    "EXACT_MATCH", patient, 1, is_dup, active_spec,
                    [f"NHS number {nhs} resolves to a single patient; surname and DOB agree."],
                )
            return Match(
                "DOB_MISMATCH", patient, 1, is_dup, active_spec,
                [
                    f"NHS number {nhs} resolves to a patient, but demographics conflict "
                    f"(referral DOB {dob} vs record {patient.get('date_of_birth')}). "
                    "Identifier vs demographic conflict = wrong-patient risk."
                ],
            )
        # NHS number supplied but not found -> fall through to demographics.

    # --- Demographic fallback -------------------------------------------
    candidates = repo.find_by_demographics(first, last, dob)
    n = len(candidates)
    if n == 0:
        why = (
            f"NHS number {nhs} not found in the EPR, and no demographic match either."
            if nhs
            else "No NHS number supplied and no demographic match in the EPR."
        )
        return Match("NO_MATCH", None, 0, notes=[why])
    if n == 1:
        patient = candidates[0]
        is_dup, active_spec = _duplicate(patient, extraction)
        why = (
            "No confirmed NHS number; name + DOB match exactly one EPR patient. "
            "Probable but unverified identity."
            if not nhs
            else f"Supplied NHS number {nhs} not found, but name + DOB match one patient. "
            "Identifier unconfirmed."
        )
        return Match("PARTIAL_MATCH", patient, 1, is_dup, active_spec, [why])
    return Match(
        "MULTIPLE_CANDIDATES", None, n,
        notes=[f"Name + DOB match {n} EPR patients; cannot safely disambiguate."],
    )
