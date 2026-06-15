# Clinical Safety Case Report (CSCR)

**Document type:** DCB0129-inspired Clinical Safety Case Report
**System:** Clinical Referral Safety Automation (UiPath REFramework + OpenMRS)
**Version:** 1.0 · **Date:** 2026-06-15 · **Author:** Clinical Safety Officer (*simulated*)

> ⚠️ **Portfolio simulation — synthetic data only. NOT a live NHS system and NOT assured or
> certified clinical software.** This report is *inspired by* DCB0129 to demonstrate
> clinical-safety reasoning; it is not a regulatory submission.

## 1. System description & intended use

The system automates the *safe, deterministic* parts of NHS-style referral intake and routes
everything else to a human. A synthetic referral letter is ingested via an Orchestrator queue;
an AI-assisted + regex-fallback extractor parses it to a schema-validated JSON; a deterministic
engine matches the patient against the EMR (OpenMRS) and applies completeness, duplicate, and
clinical-safety rules; and the bot then either:

1. **auto-creates** a referral record in OpenMRS (verified by re-read) for clean, unambiguous,
   safe cases; or
2. **routes to a human reviewer**, whose APPROVE / REJECT / AMEND decision changes the final
   outcome; or
3. raises a **Business** or **System Exception** for bad or unreadable input.

**Intended use (simulated):** decision *support and triage routing* for referral
administrators and clinicians — never autonomous clinical decision-making. **The AI proposes;
deterministic rules and humans dispose.**

**Operating context assessed:** the 15 synthetic referral scenarios in `data/input-referrals/`
with expected outcomes in `data/expected-outcomes/`; processed end to end in Phases 8–10.

## 2. Clinical risk management

Risk is managed per the [`clinical-risk-management-plan.md`](clinical-risk-management-plan.md)
(DCB0129-inspired), using the 5 × 5 matrix and acceptability criteria defined there. The hazard
register is [`hazard-log.csv`](hazard-log.csv), machine-checked by
[`validate_pack.py`](validate_pack.py).

## 3. Hazard summary

Twelve clinical hazards are identified and controlled. Residual risk after the implemented
controls:

| ID | Hazard | Initial | Residual | Control owner |
|---|---|---|---|---|
| H-01 | Referral attached to the wrong patient | High | Moderate | Software (match gate) |
| H-02 | Duplicate referral record created | High | Low | Software (dup check + idempotency) |
| H-03 | Urgent / 2WW referral delayed | High | Moderate | Software routing + human |
| H-04 | Record created from an AI mis-extraction | High | Low | Software (AI proposes only) |
| H-05 | Incomplete referral actioned | Moderate | Low | Software (completeness rules) |
| H-06 | Safeguarding / child concern unsupervised | Moderate | Moderate | Software routing + human |
| H-07 | Unreadable referral silently dropped | High | Moderate | Software (System Exception) |
| H-08 | Non-referral creates a spurious record | Low | Low | Software (Business Exception) |
| H-09 | Bot fails open and writes an unsafe record | High | Low | Software (verify-by-reread) |
| H-10 | A safety-relevant action cannot be audited | High | Low | Software (append-only audit) |
| H-11 | Referral routed to review is never resolved | High | **High** | **Deploying org (DCB0160)** |
| H-12 | Wrong reviewer decision applied, no accountability | High | Low | Software (reviewer identity + rationale) |

The single residual **High** (H-11) is an **operational** risk: the software guarantees the
referral is persisted in a durable review store and never silently dropped, but *timely
resolution* depends on the deploying organisation staffing the queue (see §6).

## 4. Safety controls & their evidence

Every control is implemented in running, tested code — not an intention. The hazard log's
**Control evidence** column points at the exact artifact; the gate fails if any reference no
longer resolves. Key control families:

- **The AI never makes a safety-critical decision (H-04).** Extraction is schema-validated
  (`services/extraction-service/schema/extraction.schema.json`) with a deterministic regex
  fallback; low confidence routes to a human (REF-013). The decision is owned by deterministic
  rules, not the model.
- **Identifier-first patient matching with a fail-safe gate (H-01).** Any match risk
  (DOB_MISMATCH / PARTIAL / MULTIPLE_CANDIDATES / NO_MATCH) blocks auto-create and routes to a
  human (`services/rules-engine/src/matcher.py`, `rules.py`; REF-004/005/006/010/011).
- **Duplicate prevention & idempotency (H-02).** Live existing-referral check plus a write
  keyed on the REF-NNN source-document id, plus queue unique-reference enforcement
  (`services/openmrs-workflow/src/referral_writer.py`; REF-007). Re-runs create no duplicates.
- **Clinical-urgency, safeguarding & completeness routing (H-03, H-05, H-06).** Red-flag,
  suspected-cancer, safeguarding, child-patient and incomplete-field signals force mandatory
  human review (REF-008/009/012).
- **Fail-safe, not fail-open (H-07, H-09).** Unreadable input raises a System Exception;
  every write is verified by re-reading it from OpenMRS, and a verify mismatch escalates rather
  than proceeds (`Process.xaml`; REF-015).
- **Business vs System exception separation (H-08).** A readable non-referral is a Business
  Exception (no retry, no record); a technical fault is a System Exception (REF-014/015).
- **Auditable by design (H-10, H-12).** Every action writes an append-only audit row; every
  human decision records a named reviewer and a mandatory rationale
  (`services/review-service/`).
- **Human-in-the-loop persistence (H-11).** A durable SQLite review store with a
  PENDING → DECIDED → RESOLVED lifecycle ensures no routed referral is lost.

Independent evidence that the controls behave as claimed: the per-phase acceptance records
(`docs/testing/phase4`–`phase10-acceptance.md`) and the Phase 10 run report, which shows **0 of
15 referrals were auto-created while carrying a safety flag**.

## 5. Safety requirements (verified)

1. No referral carrying a safety flag is ever auto-created. — *Verified: Phase 10 report, 0/15.*
2. Every risky/ambiguous/urgent/incomplete/duplicate case routes to a human. — *Verified:
   10/10 routed, Phase 8.*
3. A human decision changes the final outcome and is recorded with identity + rationale. —
   *Verified: Phase 9, 6 approved→created / 4 rejected.*
4. No duplicate EMR record on re-run. — *Verified: idempotent re-run, Phase 9.*
5. Every action is auditable. — *Verified: append-only audit log, Phases 8–9.*
6. Bad/unreadable input fails safe (BE/SE), never silently. — *Verified: REF-014, REF-015.*

## 6. Residual risk & deployment conditions

The residual risk profile is acceptable **for this simulation**. Before any non-simulated use,
the deploying organisation would need to discharge the DCB0160-side conditions, chiefly:

- **H-11 (review backlog):** staff the review queue, set resolution SLAs (especially for urgent
  cases), and monitor the PENDING backlog via the Phase 10 reporting; configure escalation for
  ageing items.
- **H-03 (urgency SLA):** define and monitor turnaround for routed 2WW/urgent referrals.
- General: CSO sign-off by a qualified clinician, DPIA completion against real data flows
  ([`../information-governance/dpia.md`](../information-governance/dpia.md)), and the explicit
  non-claims in [`safety-boundary-statement.md`](safety-boundary-statement.md).

## 7. Conclusion

With the implemented and evidenced controls, the system meets its stated safety requirements on
the assessed synthetic corpus, with no residual hazard above **Moderate** on the software side
and a single, clearly-owned operational **High** (H-11). The design principle throughout — *AI
assists, deterministic rules and humans decide, everything is audited, and the bot fails safe* —
is realised in code and demonstrated end to end.

> This conclusion is a portfolio demonstration of clinical-safety reasoning, not a statement of
> regulatory assurance.

## Related

[`clinical-risk-management-plan.md`](clinical-risk-management-plan.md) ·
[`hazard-log.csv`](hazard-log.csv) ·
[`safety-boundary-statement.md`](safety-boundary-statement.md) ·
[`../information-governance/dpia.md`](../information-governance/dpia.md) ·
[`../information-governance/dtac-assessment.md`](../information-governance/dtac-assessment.md)
