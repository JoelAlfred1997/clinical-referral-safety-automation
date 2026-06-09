/*
 * generate_build_log.js — produces docs/Build-Progress-Log.docx
 *
 * A running, human-readable log of the NHS Clinical Referral Safety Automation build.
 * UPDATE AT THE END OF EVERY PHASE: append a new phase section (see addPhase calls),
 * bump LAST_UPDATED / STATUS, then re-run:  node docs/build-log/generate_build_log.js
 *
 * Requires the global 'docx' package. Run from repo root with NODE_PATH set to the
 * npm global root (the npm script in package-less mode), e.g.:
 *   $env:NODE_PATH=(npm root -g); node docs/build-log/generate_build_log.js
 */
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, TableOfContents, HeadingLevel, BorderStyle,
  WidthType, ShadingType, Header, Footer, PageNumber, PageBreak,
} = require("docx");

const LAST_UPDATED = "9 June 2026";
const STATUS = "Phases 0, 1, 2, 3 complete  —  next: Phase 4 (Extraction & Agentic AI service)";
const OUT = path.join(__dirname, "..", "Build-Progress-Log.docx");
const CONTENT_W = 9360; // US Letter, 1" margins

// ---------- helpers ----------
const t = (text, opts = {}) => new TextRun({ text, ...opts });
const p = (children, opts = {}) =>
  new Paragraph({ children: Array.isArray(children) ? children : [t(children)], spacing: { after: 120 }, ...opts });
const h1 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [t(text)] });
const h2 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [t(text)] });
const h3 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [t(text)] });
const bullet = (text) => new Paragraph({ numbering: { reference: "bul", level: 0 }, spacing: { after: 60 },
  children: Array.isArray(text) ? text : [t(text)] });
const num = (text) => new Paragraph({ numbering: { reference: "ord", level: 0 }, spacing: { after: 60 },
  children: Array.isArray(text) ? text : [t(text)] });
const mono = (text) => t(text, { font: "Consolas", size: 20 });
const pageBreak = () => new Paragraph({ children: [new PageBreak()] });

const BORDER = { style: BorderStyle.SINGLE, size: 1, color: "BBBBBB" };
const BORDERS = { top: BORDER, bottom: BORDER, left: BORDER, right: BORDER };
function table(rows, widths, headerFill = "D5E8F0") {
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: widths,
    rows: rows.map((cells, ri) =>
      new TableRow({
        tableHeader: ri === 0,
        children: cells.map((c, ci) =>
          new TableCell({
            borders: BORDERS,
            width: { size: widths[ci], type: WidthType.DXA },
            shading: ri === 0 ? { fill: headerFill, type: ShadingType.CLEAR } : undefined,
            margins: { top: 60, bottom: 60, left: 110, right: 110 },
            children: String(c).split("\n").map((line) =>
              new Paragraph({ children: [t(line, ri === 0 ? { bold: true, size: 20 } : { size: 20 })] })),
          })),
      })),
  });
}

// ---------- phase section builder ----------
function addPhase(num_, title, blocks) {
  const out = [pageBreak(), h1(`Phase ${num_} — ${title}`)];
  for (const b of blocks) out.push(...b);
  return out;
}
const sub = (heading, paras) => [h3(heading), ...paras];

// ============================ CONTENT ============================
const children = [];

// --- Title page ---
children.push(
  new Paragraph({ spacing: { before: 2400, after: 0 }, alignment: AlignmentType.CENTER,
    children: [t("Clinical Referral Safety Automation", { bold: true, size: 48 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 },
    children: [t("Build Progress Log", { size: 32, color: "555555" })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 },
    children: [t("UiPath REFramework · OpenMRS EMR · Synthetic Data · Agentic AI · Clinical Safety Controls", { italics: true, size: 22 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 360, after: 120 },
    children: [t("⚠ Portfolio simulation — synthetic data only. Not a live NHS system.", { bold: true, size: 22, color: "B00000" })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 600 },
    children: [t(`Last updated: ${LAST_UPDATED}`, { size: 22 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [t(`Status: ${STATUS}`, { size: 22, bold: true })] }),
  pageBreak(),
);

// --- TOC ---
children.push(h1("Contents"),
  new TableOfContents("Contents", { hyperlink: true, headingStyleRange: "1-2" }),
  pageBreak());

// --- 1. The process in plain English ---
const flow = (text) => new Paragraph({ numbering: { reference: "flow", level: 0 }, spacing: { after: 80 },
  children: Array.isArray(text) ? text : [t(text)] });
children.push(
  h1("1. The process in plain English"),
  h3("The problem we are solving"),
  p("In the NHS, when a GP wants a patient seen by a specialist, they send a referral letter. Hospitals receive thousands of these. A human admin must read each one, find the right patient in the computer system, check nothing is missing, make sure it is not a duplicate, spot the urgent ones, and type it in. That is slow, repetitive, and — when it goes wrong — genuinely dangerous: wrong patient, a missed urgent (e.g. suspected-cancer) referral, or a lost letter can all cause harm."),
  p([t("This project builds a ", {}), t("robot assistant", { bold: true }), t(" that does the careful, repetitive checking automatically — but is built to know when to stop and hand a case to a human.")]),
  h3("What the robot does with one referral letter"),
  flow([t("Picks up the letter.", { bold: true }), t("  Reads the document (PDF or text) and pulls out the key facts: patient name, date of birth, NHS number, what they are referred for, how urgent it is, and who sent it.")]),
  flow([t("Looks the patient up", { bold: true }), t("  in the hospital system (OpenMRS) using those details.")]),
  flow([t("Checks it is really the right person.", { bold: true }), t("  One perfect match → good. NHS number matches but date of birth does not, or two different people match → STOP and get a human. Updating the wrong patient is the worst outcome, so it pauses rather than guess.")]),
  flow([t("Checks the letter is complete.", { bold: true }), t("  Missing the speciality, the referrer, or the clinical reason → flag it.")]),
  flow([t("Checks it is not a duplicate.", { bold: true }), t("  Has this patient already been referred to the same speciality recently? If so, flag it so two records are not created.")]),
  flow([t("Checks for danger words.", { bold: true }), t("  Terms like “suspected cancer”, “chest pain”, or safeguarding language → route to a human quickly. Urgent cases must never sit waiting.")]),
  flow([t("Makes ONE of four decisions:", { bold: true })]),
  new Paragraph({ numbering: { reference: "bul", level: 0 }, spacing: { after: 40 }, indent: { left: 900, hanging: 260 },
    children: [t("Everything clean → the robot creates the referral record in the hospital system itself.")] }),
  new Paragraph({ numbering: { reference: "bul", level: 0 }, spacing: { after: 40 }, indent: { left: 900, hanging: 260 },
    children: [t("Risky or unclear → sends it to a human review list for a person to decide.")] }),
  new Paragraph({ numbering: { reference: "bul", level: 0 }, spacing: { after: 40 }, indent: { left: 900, hanging: 260 },
    children: [t("Clearly broken (e.g. patient does not exist) → set aside as a known business problem.")] }),
  new Paragraph({ numbering: { reference: "bul", level: 0 }, spacing: { after: 80 }, indent: { left: 900, hanging: 260 },
    children: [t("Something technical broke (system down) → retry; if it still fails, raise an alert.")] }),
  flow([t("Writes everything down.", { bold: true }), t("  Every action, decision, and the reason for it is logged — a complete paper trail for the question “why did this happen?”")]),
  flow([t("Files the letter", { bold: true }), t("  into the right folder (done / needs-review / failed) and moves on to the next one.")]),
  h3("The one golden rule"),
  new Paragraph({ spacing: { before: 60, after: 120 }, border: { left: { style: BorderStyle.SINGLE, size: 18, color: "B00000", space: 12 } }, indent: { left: 200 },
    children: [t("The robot never makes the final medical decision. It does the careful checking and the safe, obvious data entry — but anything risky, urgent, or uncertain goes to a human. The AI may read and suggest; the rules and humans decide.", { italics: true, bold: true })] }),
  h3("A simple analogy"),
  p("It works like an airport security checkpoint for referral letters:"),
  bullet("Most bags (clean referrals) sail straight through."),
  bullet("A suspicious bag (missing info, wrong-patient risk, urgent) is pulled aside for a human officer to inspect."),
  bullet("Everything is on camera (the audit log)."),
  bullet("The scanner flags things, but a person decides whether to open the bag."),
  h3("Where each piece fits"),
  table([
    ["Piece", "In plain terms"],
    ["OpenMRS", "The hospital's patient computer system — where the robot looks people up and files referrals."],
    ["The 32 synthetic patients", "The fake 'people' in that system to test against — including tricky cases (two 'Helen Walsh's, a duplicate, people who do not exist)."],
    ["The referral letters (next phase)", "The incoming 'bags' to scan."],
    ["UiPath", "The actual robot that performs all the steps above."],
    ["Safety & governance documents", "The written proof that we thought through what could go wrong and how we prevent it."],
  ], [2600, 6760]),
);

// --- 2. Project at a glance ---
children.push(
  h1("2. Project at a glance"),
  p("An end-to-end Intelligent Automation portfolio project built to NHS RPA / IA standards. A synthetic referral letter is ingested via an Orchestrator queue; a UiPath REFramework bot extracts it (LLM with a deterministic regex fallback), validates the patient against OpenMRS (a real mock EPR), checks completeness, patient-match risk and duplicate risk, applies rule-based clinical-safety logic, creates a referral record in OpenMRS for safe cases or escalates risky cases to a real human-review store, writes a full audit trail, files the document, and produces reporting evidence."),
  p([t("Core principle: ", { bold: true }), t("AI assists extraction and suggested classification only. Deterministic rules and human review own every safety-sensitive outcome. The bot fails safe (escalates), never fails open (silent write).")]),
  h3("Technology stack"),
  table([
    ["Layer", "Technology", "Role"],
    ["Clinical system", "OpenMRS 3 (Docker)", "Mock EPR/EMR — patients, encounters, observations; REST + FHIR"],
    ["RPA", "UiPath Studio, REFramework, Orchestrator queue", "Orchestration, decisioning, exception/retry handling"],
    ["Extraction", "Python (LLM + regex fallback)", "Referral text → validated JSON"],
    ["Audit", "SQLite (append-only)", "who/what/before/after/when/why"],
    ["Human review", "SQLite table (Action Center optional)", "Real review records that change outcomes"],
    ["Reporting", "Excel + optional dashboard", "Run evidence and metrics"],
  ], [1700, 3100, 4560]),
  h3("Repository"),
  p([mono("E:\\Learning\\UiPath\\UiPath Tutorial & Projects\\Projects\\nhs")]),
  p([t("Key documents: ", { bold: true }), mono("README.md"), t("  ·  "), mono("docs/business/project-scope.md"), t("  ·  "), mono("docs/technical/architecture.md"), t("  ·  "), mono("docs/testing/phase1-acceptance.md"), t("  ·  "), mono("docs/testing/phase2-acceptance.md"), t("  ·  "), mono("docs/testing/phase3-acceptance.md")]),
);

// --- 2. Environment & how to run ---
children.push(
  pageBreak(), h1("3. Environment & how to run"),
  h3("Start / stop OpenMRS"),
  p([mono('docker compose -f "openmrs-setup\\docker-compose.yml" up -d')]),
  p([mono('docker compose -f "openmrs-setup\\docker-compose.yml" ps      # all four services Up')]),
  p([mono('docker compose -f "openmrs-setup\\docker-compose.yml" stop    # keep data')]),
  p([t("Readiness gate: ", { bold: true }), t("the container healthcheck reports 'healthy' BEFORE the app is ready. The real check is the REST session call returning "), mono('"authenticated":true'), t(":")]),
  p([mono("curl.exe -u admin:Admin123 http://localhost/openmrs/ws/rest/v1/session")]),
  h3("URLs & login"),
  table([
    ["What", "URL / value"],
    ["Modern UI (O3 SPA)", "http://localhost/openmrs/spa"],
    ["Legacy admin UI", "http://localhost/openmrs"],
    ["REST API base", "http://localhost/openmrs/ws/rest/v1"],
    ["FHIR R4 base", "http://localhost/openmrs/ws/fhir2/R4"],
    ["Login", "admin / Admin123"],
  ], [3000, 6360]),
  h3("Re-seed synthetic patients (idempotent)"),
  p([mono("cd openmrs-setup\\seed-data"), t("  →  "), mono("python generate_patients.py"), t("  →  "), mono("python seed_openmrs.py")]),
  h3("Environment note"),
  bullet("Windows 11 Home → Docker Desktop must use the WSL2 backend (Hyper-V backend is unavailable on Home). A broken WSL (symptom: Wsl/CallMsi/Install/REGDB_E_CLASSNOTREG) was fixed by updating WSL to v2.7.3.0."),
  bullet("First OpenMRS boot took ~45 min (one-time demo-data generation). Subsequent boots are fast (data persists in Docker volumes)."),
);

// --- 3. Resume instructions ---
children.push(
  pageBreak(), h1("4. How to resume in a new chat"),
  p("The build is done phase by phase; no phase advances until its acceptance test passes. To continue, tell the assistant the phase to proceed to (e.g. “Proceed to Phase 3”). To get back up to speed, read, in order:"),
  num([mono("README.md"), t(" — phase status table")]),
  num([mono("docs/business/project-scope.md"), t(" — full 13-phase roadmap + Definition of Done")]),
  num([mono("docs/technical/architecture.md"), t(" — architecture, data flow, design decisions")]),
  num([mono("docs/testing/phase1-acceptance.md"), t(" and "), mono("phase2-acceptance.md"), t(" — evidence + all key UUIDs")]),
  num([t("This document — running human-readable log.")]),
);

// --- Phase 0 ---
children.push(...addPhase("0", "Project Scope & Architecture", [
  sub("What was built", [
    bullet("Finalised project scope, architecture (C4 context + 13-step data flow), folder structure, data model, OpenMRS mapping, RPA design draft, and the clinical-safety boundary statement."),
    bullet("Phase-by-phase roadmap (Phases 0–13) each with its own acceptance gate, and a project-wide Definition of Done."),
  ]),
  sub("Files created", [
    table([
      ["File", "Purpose"],
      ["README.md", "Project front page + phase status"],
      [".gitignore / .env.example", "Secrets hygiene; commits fixtures, ignores runtime output"],
      ["docs/technical/architecture.md", "Architecture, data flow, design decisions"],
      ["docs/business/project-scope.md", "Scope, in/out, DoD, roadmap"],
      ["docs/clinical-safety/safety-boundary-statement.md", "AI-vs-human safety boundary"],
    ], [4200, 5160]),
  ]),
  sub("Key decisions", [
    bullet("REST-first for all bot writes (reliable, verifiable); UI automation reserved for patient search/confirm screenshots. OpenMRS O3 is a React SPA and is selector-hostile; legacy 2.x UI is the fallback."),
    bullet("“Agentic AI” scoped deliberately narrow: constrained structured extraction + suggested classification, schema-validated, behind a deterministic fallback, with zero authority over writes — framed as a safety feature."),
    bullet("Synthetic NHS numbers use the reserved 999 test range with a valid Modulus-11 check digit. Human review defaults to a real SQLite table (Action Center optional)."),
  ]),
  sub("Result", [ p("Acceptance met: architecture realistic; OpenMRS replaces a custom mock EPR; no filler system actions; suitable for an NHS RPA portfolio.") ]),
]));

// --- Phase 1 ---
children.push(...addPhase("1", "OpenMRS Local Setup", [
  sub("What was built", [
    bullet("OpenMRS 3 reference application running locally via Docker Compose (gateway + frontend + backend + MariaDB), with 50 demo patients, verified REST API and FHIR R4."),
  ]),
  sub("Files created", [
    table([
      ["File", "Purpose"],
      ["openmrs-setup/docker-compose.yml", "The 4-service OpenMRS 3 stack"],
      ["openmrs-setup/setup-notes.md", "Run/stop/reset, login, URLs, troubleshooting"],
      ["openmrs-setup/seed-data/forms-config-notes.md", "Referral → Visit/Encounter/Obs mapping plan"],
      ["docs/testing/phase1-acceptance.md", "Acceptance evidence"],
    ], [4400, 4960]),
  ]),
  sub("How to run / test", [
    p([mono('docker compose -f "openmrs-setup\\docker-compose.yml" up -d')]),
    p([mono("curl.exe -u admin:Admin123 http://localhost/openmrs/ws/rest/v1/session   # authenticated:true")]),
  ]),
  sub("Results (all PASS)", [
    bullet("REST /session → authenticated:true (admin: System Developer, Provider)."),
    bullet("Patient search works: q=John→1, q=Smith→2 (single letters return 0 — search threshold, not a bug)."),
    bullet("FHIR Patient count: 50. FHIR metadata: HTTP 200."),
    bullet("Lesson captured: container 'healthy' ≠ app ready — gate on REST /session."),
  ]),
  sub("Screenshots to capture", [
    bullet("Docker Desktop Containers view — openmrs-setup stack all green."),
    bullet("O3 login screen + home after login."),
    bullet("Patient search for 'Smith' returning results; a patient chart."),
    bullet("Terminal showing /session authenticated:true."),
  ]),
  sub("What to commit", [ p("openmrs-setup/ (compose + notes), docs/testing/phase1-acceptance.md, README update. Never commit Docker volumes or .env.") ]),
]));

// --- Phase 2 ---
children.push(...addPhase("2", "Synthetic Patient Data", [
  sub("What was built", [
    bullet("A deterministic generator and an idempotent REST seeder (Python, stdlib only) that loaded 32 synthetic patients into OpenMRS, plus a custom 'Synthetic NHS Number' identifier type."),
    bullet("Curated (not random) dataset so later phases get concrete matching fixtures: exact, DOB-mismatch, partial, multiple-candidate, duplicate-target, no-match."),
  ]),
  sub("Files created", [
    table([
      ["File", "Purpose"],
      ["openmrs-setup/seed-data/generate_patients.py", "Curated dataset + NHS Mod-11 check-digit logic"],
      ["openmrs-setup/seed-data/seed_openmrs.py", "Idempotent seeder (id type, OpenMRS ID gen, POST patients)"],
      ["data/synthetic-patients/synthetic_patients.json / .csv", "The dataset (generated)"],
      ["data/synthetic-patients/README.md", "Synthetic-data notice"],
      ["docs/testing/phase2-acceptance.md", "Acceptance evidence + key UUIDs"],
    ], [4600, 4760]),
  ]),
  sub("How to run / test", [
    p([mono("cd openmrs-setup\\seed-data"), t("  →  "), mono("python generate_patients.py"), t("  →  "), mono("python seed_openmrs.py")]),
  ]),
  sub("Results (all PASS)", [
    bullet("First seed: created=32, skipped=0, reserved(no-match)=2, failed=0."),
    bullet("Idempotent re-run: created=0, skipped=32, failed=0 (no duplicates)."),
    bullet("Search: 9990000018→1; Walsh→2 (multiple-candidate). Each patient carries OpenMRS ID (preferred) + Synthetic NHS Number (searchable)."),
    bullet("Real issue solved well: OpenMRS rejects patients lacking the required OpenMRS ID; the seeder now generates one via the idgen module REST endpoint (the same mechanism the UI uses) rather than weakening data-integrity rules."),
  ]),
  sub("Synthetic guarantees", [
    bullet("NHS numbers: reserved 999 test range, valid Modulus-11 check digit."),
    bullet("Phones: Ofcom reserved fictional range 07700 900xxx."),
  ]),
  sub("Screenshots to capture", [
    bullet("Terminal: seeder run (created=32, failed=0)."),
    bullet("Terminal: idempotent re-run (skipped=32) — strong production-grade detail."),
    bullet("O3 UI search 'Walsh' → two Helen Walsh results (wrong-patient-risk fixture)."),
    bullet("A patient chart showing the Synthetic NHS Number identifier; synthetic_patients.csv in Excel."),
  ]),
  sub("What to commit", [ p("openmrs-setup/seed-data/*.py, data/synthetic-patients/ (README + json + csv = fixtures), docs/testing/phase2-acceptance.md, README.") ]),
  sub("Deferred (tracked)", [ p("The duplicate-target patient (Arthur Reed) needs a pre-existing Referral encounter to be detectable as a duplicate. That is seeded in Phase 6/8 once the Referral encounter type + concepts exist.") ]),
]));

// --- Phase 3 ---
children.push(...addPhase("3", "Synthetic Referral Documents & Expected Outcomes", [
  sub("What was built", [
    bullet("15 synthetic GP referral documents (REF-001…REF-015) in data/input-referrals/ — the 'incoming letters' the bot will process. 14 are realistic referral letters (.txt) with a 'SYNTHETIC TEST DATA' banner; REF-015 is a deliberately corrupt PDF."),
    bullet("15 machine-readable expected-outcome files (data/expected-outcomes/REF-NNN.expected.json) — the test oracle that says, for each referral, what the correct extraction, patient-match result, safety flags, decision and final status should be."),
    bullet("Every referral is wired to a real Phase-2 seeded patient (or a reserved no-match fixture), so the scenarios exercise the actual data already in OpenMRS."),
    bullet("Expected-outcome files live OUTSIDE input-referrals/ on purpose, so the Phase 8 dispatcher never mistakes an oracle file for a referral to ingest."),
  ]),
  sub("Files created", [
    table([
      ["File", "Purpose"],
      ["data/input-referrals/REF-001…015 (.txt/.pdf)", "The 15 synthetic referral documents"],
      ["data/expected-outcomes/REF-001…015.expected.json", "Per-referral expected result (test oracle)"],
      ["data/expected-outcomes/README.md", "Oracle schema + full scenario matrix + coverage"],
      ["docs/testing/phase3-acceptance.md", "Acceptance evidence"],
    ], [4900, 4460]),
  ]),
  sub("Scenario coverage (the 15 cases)", [
    p("Spread across all four bot decisions and every safety routing reason:"),
    table([
      ["Ref", "Scenario", "Bot decision"],
      ["001 / 002 / 003", "Clean exact match, complete, routine (Bennett / Davies / Clarke)", "AUTO_CREATE_REFERRAL_RECORD"],
      ["004", "DOB mismatch (Ruby Shaw — NHS matches, DOB differs)", "HUMAN_REVIEW_REQUIRED"],
      ["005", "Partial match (Leo Hamilton — no NHS number, demographic discrepancy)", "HUMAN_REVIEW_REQUIRED"],
      ["006", "Multiple candidates (two 'Helen Walsh', same DOB)", "HUMAN_REVIEW_REQUIRED"],
      ["007", "Duplicate referral (Arthur Reed — existing active Cardiology)", "HUMAN_REVIEW_REQUIRED"],
      ["008", "Urgent 2-week-wait suspected cancer (Stanley Knight)", "HUMAN_REVIEW_REQUIRED"],
      ["009", "Safeguarding / child (Florence Cole, DOB 2018)", "HUMAN_REVIEW_REQUIRED"],
      ["010 / 011", "No match — not in OpenMRS (Maria Fernandes / Ibrahim Osei)", "HUMAN_REVIEW_REQUIRED"],
      ["012", "Incomplete — missing speciality/priority/reason (Daniel Owen)", "HUMAN_REVIEW_REQUIRED"],
      ["013", "Low extraction confidence — garbled scan/fax (Mia Roberts)", "HUMAN_REVIEW_REQUIRED"],
      ["014", "Not a referral — appointment reminder (bad input)", "BUSINESS_EXCEPTION"],
      ["015", "Corrupt / unreadable PDF (technical fault)", "SYSTEM_EXCEPTION"],
    ], [1500, 6360, 1500]),
  ]),
  sub("Decision vocabulary established (feeds Phase 5)", [
    bullet("match_result: EXACT_MATCH · DOB_MISMATCH · PARTIAL_MATCH · MULTIPLE_CANDIDATES · NO_MATCH · NOT_APPLICABLE"),
    bullet("bot_decision: AUTO_CREATE_REFERRAL_RECORD · HUMAN_REVIEW_REQUIRED · BUSINESS_EXCEPTION · SYSTEM_EXCEPTION"),
    bullet("final_status: REFERRAL_CREATED_IN_OPENMRS · ROUTED_TO_HUMAN_REVIEW · BUSINESS_EXCEPTION_FAILED · SYSTEM_EXCEPTION_ESCALATED"),
    bullet("BE vs SE distinguished on one axis: REF-014 reads fine but is the wrong document type (business); REF-015 cannot be read at all (technical → retry then escalate)."),
  ]),
  sub("Results (all PASS)", [
    bullet("15 referral inputs present; 15 expected-outcome JSON files, all validated (json.load over all 15 → 0 invalid)."),
    bullet("All match scenarios and all four bot decisions covered (AUTO_CREATE ×3, HUMAN_REVIEW ×10, BUSINESS_EXCEPTION ×1, SYSTEM_EXCEPTION ×1)."),
    bullet("Synthetic-by-construction throughout: 999-range NHS numbers, Ofcom 07700 900xxx phones, synthetic banner on every letter."),
  ]),
  sub("Screenshots to capture", [
    bullet("data/input-referrals/ folder showing the 15 referral files."),
    bullet("A clean referral (REF-001) and a tricky one (REF-006 Walsh / REF-008 2WW) opened side by side."),
    bullet("An expected-outcome JSON (e.g. REF-004.expected.json) showing the DOB-mismatch oracle."),
    bullet("data/expected-outcomes/README.md scenario matrix table."),
  ]),
  sub("What to commit", [ p("data/input-referrals/REF-* (synthetic fixtures), data/expected-outcomes/ (oracles + README), docs/testing/phase3-acceptance.md, README + this build log.") ]),
  sub("Deferred (tracked)", [ p("REF-007 duplicate needs the pre-existing Cardiology Referral encounter for Arthur Reed (seeded Phase 6/8). A few .txt referrals may optionally be re-rendered as real .pdf in Phase 4 to exercise the PDF→text path on valid PDFs.") ]),
]));

// --- Appendix A: UUIDs ---
children.push(
  pageBreak(), h1("Appendix A — Key OpenMRS UUIDs"),
  table([
    ["Resource", "UUID"],
    ["Synthetic NHS Number (identifier type)", "b3f1cb43-540d-4f2e-b4a5-2014a435cf30"],
    ["OpenMRS ID (required identifier type)", "05a29f94-c0ed-11e2-94be-8c13b969e334"],
    ["idgen source (Generator for OpenMRS ID)", "8549f706-7e85-4c1d-9424-217d50a2988b"],
    ["Location (Outpatient Clinic)", "44c3efb0-2583-4c80-a79e-1f756a03c0a1"],
    ["Telephone Number (person attribute)", "14d4f066-15f5-102d-96e4-000c29c2a5d7"],
  ], [4400, 4960]),
);

// --- Appendix B: scenario fixtures ---
children.push(
  pageBreak(), h1("Appendix B — Patient scenario fixtures"),
  p("Curated synthetic patients that drive Phase 5 patient-matching tests:"),
  table([
    ["Scenario", "Count", "Example (NHS number)"],
    ["standard (exact-match pool)", "27", "Oliver Bennett (9990000018)"],
    ["dob_mismatch_target", "1", "Ruby Shaw (9990000271)"],
    ["partial_match_target", "1", "Leo Hamilton (9990000298)"],
    ["multiple_candidate (same surname+DOB)", "2", "Helen Walsh (9990000301 / 9990000328)"],
    ["duplicate_target", "1", "Arthur Reed (9990000336)"],
    ["no_match (reserved, NOT in OpenMRS)", "2", "Maria Fernandes (9990000360), Ibrahim Osei (9990000379)"],
  ], [3700, 900, 4760]),
);

// --- Appendix C: roadmap ---
const roadmap = [
  ["0", "Scope & architecture", "✅ Done"],
  ["1", "OpenMRS local setup", "✅ Done"],
  ["2", "Synthetic patient data", "✅ Done"],
  ["3", "Synthetic referral documents (15 cases + expected outcomes)", "✅ Done"],
  ["4", "Extraction & Agentic AI service (LLM + regex + validation)", "⬜ Next"],
  ["5", "Business rules & safety decision engine", "⬜"],
  ["6", "OpenMRS workflow mapping (Referral encounter/obs)", "⬜"],
  ["7", "UiPath REFramework design spec", "⬜"],
  ["8", "UiPath build", "⬜"],
  ["9", "Human-in-the-loop review", "⬜"],
  ["10", "Reporting & dashboard", "⬜"],
  ["11", "Clinical safety & governance docs", "⬜"],
  ["12", "Testing & evidence pack", "⬜"],
  ["13", "GitHub / CV / LinkedIn packaging", "⬜"],
];
children.push(
  pageBreak(), h1("Appendix C — Phase roadmap"),
  table([["Phase", "Deliverable", "Status"], ...roadmap], [900, 6960, 1500]),
);

// ============================ DOCUMENT ============================
const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 30, bold: true, color: "1F3864", font: "Arial" },
        paragraph: { spacing: { before: 240, after: 160 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, color: "2E5496", font: "Arial" },
        paragraph: { spacing: { before: 180, after: 120 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 23, bold: true, color: "333333", font: "Arial" },
        paragraph: { spacing: { before: 140, after: 80 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 540, hanging: 260 } } } }] },
      { reference: "ord", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 540, hanging: 260 } } } }] },
      { reference: "flow", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 540, hanging: 260 } } } }] },
    ],
  },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
      children: [t("Clinical Referral Safety Automation — Build Log", { size: 16, color: "888888" })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [t("Page ", { size: 16, color: "888888" }), new TextRun({ children: [PageNumber.CURRENT], size: 16, color: "888888" }),
        t(" — synthetic data only · portfolio simulation", { size: 16, color: "888888" })] })] }) },
    children,
  }],
});

Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(OUT, buf); console.log("Wrote " + OUT + " (" + buf.length + " bytes)"); });
