# CV / LinkedIn / Interview Pack

> ⚠️ **Portfolio simulation — 100% synthetic data. Not a live NHS system.** OpenMRS is a mock EPR/EMR. AI assists extraction only; deterministic rules and human reviewers own every safety outcome.

Everything needed to present **Clinical Referral Safety Automation** on a CV, on LinkedIn, and in an
interview. All claims trace back to the generated [evidence pack](../testing/evidence-pack.md).

| File | Use it for |
|---|---|
| [`cv-linkedin-bullets.md`](cv-linkedin-bullets.md) | Copy-paste CV entries (full / compact / one-liner), LinkedIn About + launch post, skills list, elevator pitch |
| [`star-stories.md`](star-stories.md) | Seven Situation·Task·Action·Result stories for behavioural questions, each with evidence |
| [`interview-qa.md`](interview-qa.md) | Likely interview questions with grounded answers and the file to open for proof |
| [`demo-script.md`](demo-script.md) | 8–10 minute live-demo / screen-recording walkthrough, step by step |

## Headline figures (from the real run)

| Metric | Value |
|---|---|
| Synthetic referrals, end-to-end | **15** |
| Decisions matching the oracle | **15/15** |
| Created in OpenMRS | **9** (3 automated + 6 human-approved/amended) |
| Routed to human review | **10 (67%)** |
| **Auto-created while carrying a safety flag** | **0** (the core guarantee) |

Source: [`docs/testing/evidence-pack.md`](../testing/evidence-pack.md) — generated, not hand-typed.

## Acceptance gate

This pack is machine-checked. From the repo root:

```bash
python docs/cv-linkedin/validate_pack.py
```

It verifies the deliverables exist, every doc carries the synthetic-data banner, the README phase table
is complete, all internal links resolve, and the headline figures quoted here match the evidence pack.
Recorded result: [`docs/testing/phase13-acceptance.md`](../testing/phase13-acceptance.md).
