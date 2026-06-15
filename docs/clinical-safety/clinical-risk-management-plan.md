# Clinical Risk Management Plan (CRMP)

**Document type:** DCB0129-inspired Clinical Risk Management Plan
**System:** Clinical Referral Safety Automation (UiPath REFramework + OpenMRS)
**Version:** 1.0 · **Date:** 2026-06-15

> ⚠️ **Portfolio simulation — synthetic data only. This is NOT a live NHS system and NOT
> assured or certified clinical software.** This plan is *inspired by* DCB0129 to
> demonstrate clinical-risk-management thinking; it is not a regulatory submission. The
> Clinical Safety Officer role described below is a **simulated** role for this portfolio.

## 1. Purpose & scope

This plan defines how clinical risk is identified, assessed, controlled, and evidenced for
the referral-intake automation. It covers the manufacturer-side activities (design and build
of the bot and its services); operational deployment activities that a real provider would own
are flagged as **DCB0160-inspired / operational** where they arise (notably H-11).

**Scope of the system assessed:** ingestion of a referral document → AI-assisted extraction →
deterministic patient matching and safety rules → either an automated record in the EMR
(OpenMRS), or routing to a human reviewer whose decision changes the outcome, or a
business/system exception — with full audit logging. The 15 synthetic referral scenarios
(`data/input-referrals/`, oracles in `data/expected-outcomes/`) are the worked corpus.

**Out of scope:** any real NHS system/data/network; the LLM model internals; the clinical
correctness of a *human* reviewer's decision; production infosec hardening.

## 2. Roles & responsibilities (simulated)

| Role | Responsibility |
|---|---|
| Clinical Safety Officer (CSO) — *simulated* | Owns the hazard log and this plan; signs off residual risk; would, in a real deployment, be a suitably qualified clinician. |
| Developer / manufacturer | Implements and evidences the safety controls in code; keeps control evidence traceable to the hazard log. |
| Deploying organisation — *DCB0160* | Owns operational controls (staffing the review queue, SLAs, training, incident reporting). Responsible for H-11. |

## 3. Risk management process

The lifecycle mirrors DCB0129: **identify hazards → assess initial risk → define controls →
assess residual risk → accept or iterate → maintain the log**. Each phase of this build
produced a control and the evidence for it (see [`clinical-safety-case-report.md`](clinical-safety-case-report.md) §4),
so the hazard log is traceable to running, tested code rather than intentions.

## 4. Risk evaluation matrix (5 × 5)

**Likelihood:** Very low · Low · Medium · High · Very high
**Severity:** Minor · Significant · Considerable · Major · Catastrophic

| Likelihood \ Severity | Minor | Significant | Considerable | Major | Catastrophic |
|---|---|---|---|---|---|
| **Very high** | Moderate | High | High | Unacceptable | Unacceptable |
| **High** | Low | Moderate | High | High | Unacceptable |
| **Medium** | Low | Moderate | Moderate | High | High |
| **Low** | Low | Low | Moderate | Moderate | High |
| **Very low** | Low | Low | Low | Moderate | Moderate |

**Acceptability criteria:**

- **Low** — acceptable; no further action beyond the existing control.
- **Moderate** — acceptable with the documented control and ongoing monitoring (audit log + reporting).
- **High** — only acceptable in this simulation with a named control *and* a stated operational
  requirement; would require CSO sign-off and review before live use.
- **Unacceptable** — must not operate; redesign required. *(No residual hazard sits here.)*

## 5. Hazard log

The live register is [`hazard-log.csv`](hazard-log.csv) (machine-checked by
[`validate_pack.py`](validate_pack.py)). It records, per hazard: causes, clinical effect, the
named existing control(s), **control evidence** (the actual file / scenario that implements
it), and initial vs residual risk. Twelve hazards are currently logged (H-01–H-12).

## 6. Residual risk summary

After the implemented controls, **no hazard remains High on the manufacturer side**; the only
residual **High** is H-11 (review-queue backlog), which is an **operational** risk owned by
the deploying organisation under DCB0160 — the software guarantees the referral is *persisted
and never silently dropped*, but timely resolution depends on staffing the queue. All other
residual risks are **Low** or **Moderate** and are accepted with the audit trail and reporting
(Phase 10) providing ongoing monitoring.

## 7. Maintenance

The hazard log is updated whenever a control changes or a new scenario is added. Every change
to a control must keep its **control evidence** reference valid — `validate_pack.py` fails the
build if a referenced artifact no longer exists, so the safety case cannot silently rot.

## Related

[`clinical-safety-case-report.md`](clinical-safety-case-report.md) ·
[`hazard-log.csv`](hazard-log.csv) ·
[`safety-boundary-statement.md`](safety-boundary-statement.md) ·
[`../information-governance/dpia.md`](../information-governance/dpia.md)
