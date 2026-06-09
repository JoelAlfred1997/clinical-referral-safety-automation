# Expected outcomes — referral scenario matrix

**Synthetic data only.** One `REF-NNN.expected.json` here describes the *expected*
end-to-end result for the matching referral file in `../input-referrals/`.

These files live **outside** `input-referrals/` on purpose: the Phase 8 dispatcher scans
`input-referrals/` and would otherwise try to ingest an expected-outcome file as a referral.

They are the test oracle for Phases 4–12 (extraction, rules/decision engine, build, testing).

## Schema (per file)

| Field | Meaning |
|---|---|
| `referral_id` / `source_file` | links to the input referral |
| `scenario` | short scenario key |
| `patient_ref` | the real seeded patient (or reserved no-match fixture) this referral targets |
| `expected_extraction` | the field values a correct extractor should return |
| `expected_missing_fields` | mandatory fields the extractor should report absent |
| `expected_confidence` | high / medium / low / n/a |
| `expected_match_result` | EXACT_MATCH · DOB_MISMATCH · PARTIAL_MATCH · MULTIPLE_CANDIDATES · NO_MATCH · NOT_APPLICABLE |
| `expected_safety_flags` | safety flags the rule engine should raise |
| `expected_reason_codes` | reason code(s) driving the decision |
| `expected_bot_decision` | AUTO_CREATE_REFERRAL_RECORD · HUMAN_REVIEW_REQUIRED · BUSINESS_EXCEPTION · SYSTEM_EXCEPTION |
| `expected_final_status` | REFERRAL_CREATED_IN_OPENMRS · ROUTED_TO_HUMAN_REVIEW · BUSINESS_EXCEPTION_FAILED · SYSTEM_EXCEPTION_ESCALATED |

## Matrix

| Ref | Patient (NHS) | In OpenMRS | Match result | Key reason code(s) | Bot decision |
|---|---|---|---|---|---|
| REF-001 | Oliver Bennett (9990000018) | yes | EXACT_MATCH | MATCH_EXACT | AUTO_CREATE_REFERRAL_RECORD |
| REF-002 | George Davies (9990000034) | yes | EXACT_MATCH | MATCH_EXACT | AUTO_CREATE_REFERRAL_RECORD |
| REF-003 | Amelia Clarke (9990000026) | yes | EXACT_MATCH | MATCH_EXACT | AUTO_CREATE_REFERRAL_RECORD |
| REF-004 | Ruby Shaw (9990000271) | yes | DOB_MISMATCH | MATCH_DOB_MISMATCH | HUMAN_REVIEW_REQUIRED |
| REF-005 | Leo Hamilton (9990000298) | yes | PARTIAL_MATCH | MATCH_PARTIAL | HUMAN_REVIEW_REQUIRED |
| REF-006 | Helen Walsh (9990000301 / 9990000328) | yes (×2) | MULTIPLE_CANDIDATES | MATCH_MULTIPLE_CANDIDATES | HUMAN_REVIEW_REQUIRED |
| REF-007 | Arthur Reed (9990000336) | yes | EXACT_MATCH | DUPLICATE_REFERRAL | HUMAN_REVIEW_REQUIRED |
| REF-008 | Stanley Knight (9990000352) | yes | EXACT_MATCH | URGENT_RED_FLAG | HUMAN_REVIEW_REQUIRED |
| REF-009 | Florence Cole (9990000344) | yes | EXACT_MATCH | SAFEGUARDING / CHILD_PATIENT | HUMAN_REVIEW_REQUIRED |
| REF-010 | Maria Fernandes (9990000360) | no (reserved) | NO_MATCH | MATCH_NONE | HUMAN_REVIEW_REQUIRED |
| REF-011 | Ibrahim Osei (9990000379) | no (reserved) | NO_MATCH | MATCH_NONE | HUMAN_REVIEW_REQUIRED |
| REF-012 | Daniel Owen (9990000166) | yes | EXACT_MATCH | INCOMPLETE_MANDATORY_FIELDS | HUMAN_REVIEW_REQUIRED |
| REF-013 | Mia Roberts (9990000085) | yes | EXACT_MATCH | LOW_EXTRACTION_CONFIDENCE | HUMAN_REVIEW_REQUIRED |
| REF-014 | (not a referral) | n/a | NOT_APPLICABLE | NOT_A_REFERRAL | BUSINESS_EXCEPTION |
| REF-015 | (corrupt PDF) | n/a | NOT_APPLICABLE | FILE_UNREADABLE | SYSTEM_EXCEPTION |

## Coverage

- **Bot decisions:** AUTO_CREATE ×3, HUMAN_REVIEW ×10, BUSINESS_EXCEPTION ×1, SYSTEM_EXCEPTION ×1.
- **Match results:** exact, DOB-mismatch, partial, multiple-candidate, no-match, not-applicable.
- **Safety routing reasons:** patient-match risk, duplicate, urgent/2WW cancer, safeguarding/child,
  incomplete, low confidence, not-a-referral, unreadable file.

## Known dependencies

- **REF-007 (duplicate):** requires the pre-existing active Cardiology Referral encounter for
  Arthur Reed (9990000336) to be seeded — that happens in Phase 6/8 once the `Referral` encounter
  type and concepts exist. Until then the duplicate check cannot fully execute.
- Reason codes / decision and status enums above are the working vocabulary for the Phase 5 rules
  engine; they may be refined when that engine is built, but the scenarios will not change.
