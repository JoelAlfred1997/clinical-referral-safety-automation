"""
generate_patients.py  —  Phase 2: synthetic patient dataset generator.

Produces a deterministic, curated set of >=30 SYNTHETIC patients and writes them to
  data/synthetic-patients/synthetic_patients.json
  data/synthetic-patients/synthetic_patients.csv

ALL DATA IS SYNTHETIC. NOT REAL PATIENTS.
  - NHS numbers: reserved 999 test range with a valid Modulus-11 check digit.
  - Phones: Ofcom reserved fictional range 07700 900xxx.

The dataset is curated (not random) so later phases get concrete fixtures for
exact / dob-mismatch / partial / multiple-candidate / duplicate / no-match scenarios.

Stdlib only. Run:  python generate_patients.py
"""
from __future__ import annotations
import csv
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "data" / "synthetic-patients"


def nhs_check_digit(nine_digits: str) -> int | None:
    """Modulus-11 check digit for the first 9 digits of an NHS number.
    Returns the check digit (0-9), or None if the result is 10 (an invalid NHS number)."""
    assert len(nine_digits) == 9 and nine_digits.isdigit()
    total = sum(int(d) * w for d, w in zip(nine_digits, range(10, 1, -1)))
    remainder = total % 11
    check = 11 - remainder
    if check == 11:
        check = 0
    if check == 10:
        return None  # caller must skip this base
    return check


def next_valid_nhs(counter: int) -> tuple[str, int]:
    """Return (10-digit NHS number in the 999 test range, next counter).
    Skips any 9-digit base whose check digit would be 10 (invalid)."""
    while True:
        nine = "999" + f"{counter:06d}"
        cd = nhs_check_digit(nine)
        counter += 1
        if cd is not None:
            return nine + str(cd), counter


# --- Curated base patients (NHS number assigned programmatically below) ---------------
# fields: first, last, dob (YYYY-MM-DD), gender (M/F), postcode, gp_practice,
#         conditions (list), existing_referral_status, scenario, seed (bool)
_BASE = [
    # ----- standard exact-match pool -----
    ("Oliver",   "Bennett",   "1979-04-12", "M", "LS6 2AF",  "The Grange Medical Practice",      ["Hypertension"],                 "none",            "standard", True),
    ("Amelia",   "Clarke",    "1990-11-23", "F", "M14 5GL",  "Didsbury Health Centre",           ["Asthma"],                       "none",            "standard", True),
    ("George",   "Davies",    "1965-02-09", "M", "B12 9QR",  "Selly Oak Surgery",                ["Type 2 diabetes", "Hypertension"], "none",         "standard", True),
    ("Isla",     "Evans",     "2001-07-30", "F", "NE4 6RT",  "Westgate Medical Group",           [],                               "none",            "standard", True),
    ("Harry",    "Foster",    "1958-12-01", "M", "S2 4QW",   "Heeley Green Surgery",             ["COPD"],                         "none",            "standard", True),
    ("Ava",      "Griffiths", "1986-05-17", "F", "CF24 3AA", "Roath Park Surgery",               ["Migraine"],                     "none",            "standard", True),
    ("Jack",     "Hughes",    "1973-09-08", "M", "L8 7NX",   "Princes Park Health Centre",       [],                               "none",            "standard", True),
    ("Mia",      "Roberts",   "1995-03-26", "F", "BS5 9QY",  "Lawrence Hill Surgery",            ["Anxiety"],                      "none",            "standard", True),
    ("Charlie",  "Walker",    "1969-08-14", "M", "LE2 1TR",  "Clarendon Park Medical Centre",    ["Hypertension", "High cholesterol"], "none",       "standard", True),
    ("Grace",    "Wright",    "1982-01-19", "F", "NG7 2BU",  "Lenton Medical Practice",          [],                               "none",            "standard", True),
    ("Thomas",   "Green",     "1977-06-05", "M", "OX4 1EE",  "Cowley Road Medical Practice",     ["Lower back pain"],              "none",            "standard", True),
    ("Sophie",   "Hall",      "1993-10-11", "F", "CB1 2JD",  "Mill Road Surgery",                [],                               "none",            "standard", True),
    ("James",    "Wood",      "1961-03-22", "M", "HD1 5JP",  "Greenhead Family Practice",        ["Osteoarthritis"],               "none",            "standard", True),
    ("Lily",     "Jenkins",   "1988-12-29", "F", "SA1 3SN",  "Uplands Surgery",                  ["Hypothyroidism"],               "none",            "standard", True),
    ("Daniel",   "Owen",      "1974-04-03", "M", "PL4 8NF",  "Mutley Plain Practice",            [],                               "none",            "standard", True),
    ("Ella",     "Morgan",    "1999-09-15", "F", "EX1 2QS",  "St Thomas Medical Group",          ["Eczema"],                       "none",            "standard", True),
    ("William",  "Phillips",  "1956-07-27", "M", "DH1 4QX",  "Claypath Medical Practice",        ["Atrial fibrillation"],          "none",            "standard", True),
    ("Chloe",    "Edwards",   "1991-02-18", "F", "YO10 3HE", "Heworth Green Surgery",            [],                               "none",            "standard", True),
    ("Joshua",   "Lewis",     "1984-11-06", "M", "RG1 5AX",  "London Road Surgery",              ["Depression"],                   "none",            "standard", True),
    ("Freya",    "Harris",    "1968-05-21", "F", "GL1 3PX",  "Gloucester City Practice",         ["Hypertension"],                 "none",            "standard", True),
    ("Samuel",   "Patel",     "1980-08-02", "M", "LU1 1HR",  "Bury Park Medical Centre",         ["Type 2 diabetes"],              "none",            "standard", True),
    ("Poppy",    "Khan",      "1997-01-09", "F", "BD3 9LP",  "Little Horton Lane Surgery",       [],                               "none",            "standard", True),
    ("Henry",    "Ahmed",     "1971-10-25", "M", "HA0 4LP",  "Wembley Family Practice",          ["Asthma"],                       "none",            "standard", True),
    ("Evie",     "Begum",     "1994-06-13", "F", "E1 5JP",   "Spitalfields Practice",            [],                               "none",            "standard", True),
    ("Alfie",    "Murphy",    "1963-03-30", "M", "BT9 6AD",  "Lisburn Road Surgery",             ["Ischaemic heart disease"],      "none",            "standard", True),

    # ----- DOB-mismatch target (referral will carry this NHS but a wrong DOB) -----
    ("Ruby",     "Shaw",      "1985-09-04", "F", "ST4 2RW",  "Hartshill Medical Centre",         ["Hypertension"],                 "none",            "dob_mismatch_target", True),

    # ----- partial-match target (referral omits NHS; match surname+DOB+postcode) -----
    ("Leo",      "Hamilton",  "1976-12-16", "M", "AB10 6RN", "Carden Medical Practice",          ["High cholesterol"],             "none",            "partial_match_target", True),

    # ----- multiple-candidate pair: SAME surname + SAME DOB, different NHS/postcode -----
    ("Helen",    "Walsh",     "1975-03-12", "F", "CV1 2AB",  "Foleshill Road Surgery",           ["Hypothyroidism"],               "none",            "multiple_candidate", True),
    ("Helen",    "Walsh",     "1975-03-12", "F", "WS1 3QT",  "Palfrey Health Centre",            ["Asthma"],                       "none",            "multiple_candidate", True),

    # ----- duplicate target: has an existing active referral (Cardiology) -----
    ("Arthur",   "Reed",      "1959-11-28", "M", "TS1 2NX",  "Linthorpe Surgery",                ["Atrial fibrillation", "Hypertension"], "active:Cardiology", "duplicate_target", True),

    # ----- urgent/safeguarding flavour (still standard match, supports Phase 3 referrals) -----
    ("Florence", "Cole",      "2018-02-14", "F", "WF1 4AL",  "Eastmoor Health Centre",           ["Safeguarding alert"],           "none",            "standard", True),
    ("Stanley",  "Knight",    "1949-06-19", "M", "DN1 2EE",  "St Vincent Medical Practice",      ["Suspected lung lesion on CXR"], "none",            "standard", True),

    # ----- no-match: referenced by a referral but DELIBERATELY NOT loaded into OpenMRS -----
    ("Maria",    "Fernandes", "1983-07-21", "F", "PO1 2EP",  "Portsea Island Practice",          [],                               "none",            "no_match", False),
    ("Ibrahim",  "Osei",      "1990-04-08", "M", "M1 1AE",   "Ardwick Green Surgery",            [],                               "none",            "no_match", False),
]


def build() -> list[dict]:
    patients: list[dict] = []
    counter = 1
    for i, (first, last, dob, gender, postcode, gp, conditions, refstatus, scenario, seed) in enumerate(_BASE, start=1):
        nhs, counter = next_valid_nhs(counter)
        patients.append({
            "synthetic_id": f"SYN-{i:03d}",
            "nhs_number": nhs,
            "first_name": first,
            "last_name": last,
            "date_of_birth": dob,
            "gender": gender,
            "postcode": postcode,
            "phone": f"07700 900{i:03d}",          # Ofcom fictional range
            "gp_practice": gp,
            "conditions": conditions,
            "existing_referral_status": refstatus,
            "scenario": scenario,
            "seed_to_openmrs": seed,
            "is_synthetic": True,
        })
    return patients


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    patients = build()

    # sanity: all NHS numbers valid + unique
    nums = [p["nhs_number"] for p in patients]
    assert len(set(nums)) == len(nums), "duplicate NHS numbers generated"
    for n in nums:
        assert nhs_check_digit(n[:9]) == int(n[9]), f"bad check digit: {n}"

    (OUT_DIR / "synthetic_patients.json").write_text(
        json.dumps(patients, indent=2), encoding="utf-8")

    csv_cols = ["synthetic_id", "nhs_number", "first_name", "last_name", "date_of_birth",
                "gender", "postcode", "phone", "gp_practice", "conditions",
                "existing_referral_status", "scenario", "seed_to_openmrs"]
    with (OUT_DIR / "synthetic_patients.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=csv_cols)
        w.writeheader()
        for p in patients:
            row = dict(p)
            row["conditions"] = "; ".join(p["conditions"])
            w.writerow({k: row[k] for k in csv_cols})

    seeded = sum(1 for p in patients if p["seed_to_openmrs"])
    by_scn: dict[str, int] = {}
    for p in patients:
        by_scn[p["scenario"]] = by_scn.get(p["scenario"], 0) + 1
    print(f"Generated {len(patients)} synthetic patients ({seeded} to seed, "
          f"{len(patients) - seeded} reserved no-match).")
    print("By scenario:", ", ".join(f"{k}={v}" for k, v in sorted(by_scn.items())))
    print("Wrote:", OUT_DIR / "synthetic_patients.json")
    print("Wrote:", OUT_DIR / "synthetic_patients.csv")


if __name__ == "__main__":
    main()
