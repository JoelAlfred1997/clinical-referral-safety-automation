# Review service — human-in-the-loop (Phase 9)

The **real review store** and the loop that lets a clinician's decision **change
the final outcome** of a referral the bot was not allowed to auto-create.

In Phase 8 the REFramework bot routed 10 risky/ambiguous referrals (wrong-patient
risk, duplicate, no-match, incomplete, low-confidence, urgent) to human review and
left them `PENDING`. Phase 9 closes that loop:

```
 Phase 8 bot ──routes──▶  review store (SQLite)
                              │  PENDING
        clinician ──decides──▶│  DECIDED   (APPROVE / REJECT / AMEND + who + why)
        the bot   ──applies──▶│  RESOLVED  (OpenMRS create  /  no record)
                              ▼
                     audit log + OpenMRS
```

Standard library only (`sqlite3`, `http.server`, `urllib`) — no third-party
dependencies, same as the other services. **All data is synthetic.**

## Pieces

| File | Role |
|---|---|
| `src/review_store.py` | The SQLite store: schema, idempotent ingest, the `PENDING → DECIDED → RESOLVED/FAILED` state machine. The row is the human-decision audit trail (who/what/before/after/when/why). |
| `init_store.py` | Ingest the Phase 8 `data/review/review-store.csv` PENDING rows into SQLite (idempotent). |
| `record_decision.py` | **The reviewer action.** Records APPROVE / REJECT / AMEND with the clinician's identity and a mandatory rationale. Does not touch OpenMRS. |
| `resolve_reviews.py` | **The bot re-read.** Applies each decision: APPROVE/AMEND → create in OpenMRS via the writeback service (`:8091`); REJECT → no record. Writes an audit row per outcome. Idempotent. |
| `app.py` | HTTP service on `:8092` (`/health`, `/reviews`, `/reviews/<id>/decision`, `/resolve`) so the UiPath **ReviewResolver** process can drive it. |
| `validate_acceptance.py` | Self-contained Phase 9 gate: ingest → scripted worklist → resolve → assert outcomes changed + idempotent. |

## The store (`data/review/review-store.sqlite`)

One row per referral under review. Key columns: `review_status`
(`PENDING/DECIDED/RESOLVED/FAILED`), `reviewer`, `reviewer_decision`,
`rationale`, `confirmed_nhs_number`, `amended_fields` (JSON), `final_status`,
`encounter_uuid`, and `routed/created/decided/resolved` timestamps. Gitignored
(runtime, environment-specific) — rebuild any time with `init_store.py`.

`final_status` extends the Phase 3 vocabulary:
`REFERRAL_CREATED_IN_OPENMRS` (approved/amended) ·
`REVIEW_REJECTED_NO_RECORD` (rejected) ·
`REVIEW_RESOLUTION_FAILED` (system fault while applying — stays actionable).

## Run the loop

```bash
# prerequisites: OpenMRS up, writeback service (:8091) running
cd services/review-service

python init_store.py                      # 10 PENDING from the Phase 8 review CSV

# a clinician works the list (examples — see record_decision.py --help)
python record_decision.py REF-005 --reviewer "Dr A Okonkwo" --approve \
    --nhs 9990000298 --rationale "Identity confirmed against PAS; safe to create."
python record_decision.py REF-007 --reviewer "Dr A Okonkwo" --reject \
    --rationale "Active referral already exists; duplicate, return to GP."
python record_decision.py REF-013 --reviewer "Dr A Okonkwo" --amend \
    --set specialty=Dermatology --set priority=Routine \
    --set reason_for_referral="Suspicious pigmented lesion; assess." \
    --rationale "Fields confirmed with GP after re-reading the fax."

python resolve_reviews.py --dry-run       # preview, change nothing
python resolve_reviews.py                 # the bot applies the decisions

# or drive it over HTTP (what the UiPath ReviewResolver does):
python app.py &                           # :8092
curl -s -X POST http://localhost:8092/resolve
```

## Acceptance

```bash
python validate_acceptance.py             # OpenMRS + writeback(:8091) must be up
```
Asserts: 10 ingested → 10 decided (rationale enforced) → resolve yields **6 created
in OpenMRS + 4 rejected, 0 failed**, every `final_status` matches the clinician's
decision, each create has a verified `encounter_uuid`, and a second resolve actions
**0** (no duplicate OpenMRS records).

## Scope boundary

The reviewer here is driven by a CLI / REST call standing in for a clinician
working a worklist — the project is a portfolio simulation, not a clinical UI.
What is real: the SQLite store, the enforced who/why audit, the state machine, and
the OpenMRS create/verify via the proven Phase 6 writer. Reporting on this run is
Phase 10.
