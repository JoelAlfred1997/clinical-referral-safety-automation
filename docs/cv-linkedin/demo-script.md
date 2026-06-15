# Demo Script — Clinical Referral Safety Automation

> ⚠️ **Portfolio simulation — 100% synthetic data. Not a live NHS system.** OpenMRS is a mock EPR/EMR. AI assists extraction only; deterministic rules and human reviewers own every safety outcome.

A tight, repeatable walkthrough for a **live demo, a screen recording, or an interview share-screen**. Target length: **8–10 minutes**. Each step lists *what to do*, *what to say*, and *what to show on screen*.

---

## 0. Before you start (off-camera setup)

Have these ready so the demo is smooth:

1. Docker running OpenMRS: `docker compose -f openmrs-setup/docker-compose.yml up -d`
   — wait until `GET /openmrs/ws/rest/v1/session` returns `authenticated:true`.
2. Three Python services running (each `python app.py`):
   - extraction `:8089`, decision `:8090`, OpenMRS writeback `:8091`
   - review service `:8092` (`services/review-service/app.py`)
3. `uip login` valid (org/tenant) and the `NHS_Referrals` Orchestrator queue present in folder `Shared`.
4. Two browser tabs open: OpenMRS SPA (`http://localhost/openmrs/spa`) and the dashboard
   (`reports/dashboard.html` opened from disk).
5. A terminal at the repo root.

> If you only have a few minutes, skip the live run and demo from the **already-generated evidence**
> (steps 5–7): the dashboard, the Excel workbook, and the evidence pack tell the whole story without
> waiting on services.

---

## 1. Frame the problem (60s)

**Do:** open `README.md` (or the GitHub front page).

**Say:**
> "NHS referral intake is high-volume and safety-critical. The expensive failures are wrong-patient
> matching, duplicate referrals, and urgent two-week-wait cancer cases slipping through. I built a
> UiPath bot that automates the *safe, deterministic* parts of intake and routes every risky or
> ambiguous case to a human — and proves it with auditable evidence. Everything here is synthetic
> data against OpenMRS as a mock EPR."

**Show:** the synthetic-data banner at the top of the README and the capabilities line.

---

## 2. Show the architecture (60s)

**Do:** open [`docs/technical/architecture.md`](../technical/architecture.md).

**Say:**
> "One referral is one transaction. A Dispatcher pushes each letter onto an Orchestrator queue. A
> REFramework Performer extracts the letter — LLM with a deterministic regex fallback — validates the
> patient against OpenMRS over REST, runs duplicate and clinical-safety rules, then branches: create
> the record, send it to human review, or raise a business/system exception. Every step writes an
> audit row."

**Show:** the C4 context diagram and the 13-step data-flow list.

**Key talking point:** *"The AI only proposes. Deterministic rules and humans decide. In a clinical-safety
context that restraint is the design, not a limitation."*

---

## 3. Show an input referral and its oracle (45s)

**Do:** open `data/input-referrals/REF-007-*.txt` and `data/expected-outcomes/REF-007.expected.json`.

**Say:**
> "I wrote 15 synthetic referrals covering every scenario — clean matches, DOB mismatch, partial and
> multiple matches, a duplicate, an urgent 2WW cancer, a safeguarding child, no-match, incomplete
> fields, a degraded scan, plus a not-a-referral and a corrupt file. Each one has an expected-outcome
> *oracle* I wrote first, so the build is tested against a spec, not against itself. REF-007 here is
> the duplicate — the expected decision is *human review*, not auto-create."

**Show:** the referral text, then the matching oracle with `bot_decision: HUMAN_REVIEW_REQUIRED` and
reason code `DUPLICATE_REFERRAL`.

---

## 4. Run the bot live (2–3 min)

**Do (terminal):**
```bash
# (one-time per clean demo) restore inputs the previous run moved out
git checkout -- data/input-referrals

# Dispatcher: enqueue all REF-* as queue items
cd uipath/NHS.ReferralSafety.Dispatcher
uip rpa run --file-path Main.xaml --skip-build

# Performer: process the queue end-to-end
cd ../NHS.ReferralSafety.Performer
uip rpa run --file-path Main.xaml --skip-build
```

**Say while it runs:**
> "The Dispatcher is creating queue items with a unique reference per referral. Now the REFramework
> Performer picks them up one at a time. For each one it's calling the extraction service, the decision
> service, and writing to OpenMRS for the clean ones — REF-001 to 003. The risky ten are being written
> to a real SQLite review store, not just logged. REF-014 raises a *business* exception because it
> isn't a referral; REF-015 raises a *system* exception because the file is corrupt — and those two are
> handled differently, which matters for retries."

**Show:** the run logs scrolling; point out a couple of `AUTO_CREATE`, several `HUMAN_REVIEW`, and the
two exceptions.

---

## 5. Prove it in OpenMRS (60s)

**Do:** in the OpenMRS SPA, search a patient who got an auto-created referral (e.g. Bennett / REF-001)
and open their visit/encounters.

**Say:**
> "This is the real EMR. The bot didn't log a message saying it created a referral — it created a
> Referral encounter with observations over REST, then re-read it to verify. Re-running the bot does
> *not* create a duplicate; idempotency is keyed on the referral reference."

**Show:** the Referral encounter and its observations in OpenMRS.

---

## 6. Human-in-the-loop changes the outcome (90s)

**Do (terminal):** record a clinician decision, then let the bot act on it.
```bash
cd services/review-service
# Approve a held referral (e.g. REF-005 partial match) with reviewer identity + rationale
python record_decision.py REF-005 APPROVE --reviewer "Dr A. Smith" --rationale "Identity confirmed by phone"
# REJECT the duplicate so no record is created
python record_decision.py REF-007 REJECT --reviewer "Dr A. Smith" --rationale "Duplicate of active Cardiology referral"
# Bot re-reads decisions and resolves them
python resolve_reviews.py
```

**Say:**
> "Here's the part that makes it real. A clinician approves REF-005 and rejects the duplicate REF-007,
> each with their identity and a rationale. The bot then re-reads those decisions: the approved one gets
> written into OpenMRS, the rejected one gets *no* record. The human decision genuinely changes the
> outcome — and both actions are appended to the audit log."

**Show:** the new Referral encounter for REF-005 in OpenMRS; confirm REF-007 produced nothing.

---

## 7. The evidence: dashboard, report, audit (2 min)

**Do:** open `reports/dashboard.html`, then `reports/referral-safety-report.xlsx`, then
`data/audit/audit-log.csv`.

**Say:**
> "Nothing here is hand-typed. The dashboard and the Excel workbook are generated from the real run —
> the decision artifacts, the review store, and the audit log. Headline: 15 referrals, all 15 matching
> the oracle. Nine ended up in OpenMRS — three fully automated and six after a human approved or
> amended them. Four were rejected at review, two were exceptions. The number I care about most is
> **zero**: zero referrals were ever auto-created while carrying a safety flag. That's the core
> guarantee, and it's machine-checked."

**Show, in order:**
- Dashboard donut + bars (outcomes), the "0 unsafe auto-creates" figure.
- Excel: the *Audit trail* sheet — who/what/before/after/when/why.
- `audit-log.csv`: 25 append-only rows.

---

## 8. Governance + how it's tested (60s)

**Do:** open [`docs/clinical-safety/hazard-log.csv`](../clinical-safety/hazard-log.csv) and
[`docs/testing/evidence-pack.md`](../testing/evidence-pack.md).

**Say:**
> "Because this is clinical, I wrote a DCB0129/0160-inspired safety pack: 12 named hazards, each mapped
> to a real control in the code, with initial and residual risk scored on a 5×5 matrix. The evidence
> pack is generated and machine-checked — a single gate re-derives every claim from the artifacts and
> compares against the committed docs so they can't drift."

**Do (terminal, optional finale):**
```bash
python services/testing/validate_acceptance.py    # → 8/8
python docs/clinical-safety/validate_pack.py       # → 9/9
```

**Say:**
> "Green across the board. That's the project: automate the safe parts, route the rest to a human,
> prove every step."

---

## 9. Close (30s)

**Say:**
> "To summarise — REFramework with Orchestrator queues, AI-assisted extraction behind a deterministic
> guardrail, real REST writes to an EMR, a real human-review loop, append-only audit, and a clinical-
> safety governance pack. Built phase by phase, each phase gated by an acceptance test before the next
> one started. Happy to go deep on any part."

---

## Quick reference — the numbers (memorise these)

| Metric | Value |
|---|---|
| Synthetic referrals, end-to-end | **15** |
| Decisions matching the oracle | **15/15** |
| Created in OpenMRS | **9** (3 automated + 6 human-approved/amended) |
| Routed to human review | **10 (67%)** |
| Rejected at review (no record) | **4** |
| Exceptions (business + system) | **2** |
| **Auto-created while carrying a safety flag** | **0** (the core guarantee) |
| Append-only audit rows | **25** |
| Named hazards in the safety pack | **12** |
| Machine-checked acceptance gates | **11 prior + Phase 12 consolidation** |

*All figures come from [`docs/testing/evidence-pack.md`](../testing/evidence-pack.md), generated from the real run.*
