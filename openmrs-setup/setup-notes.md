# OpenMRS Local Setup — Phase 1

> Mock EPR/EMR for the NHS Clinical Referral Safety Automation portfolio project.
> **Synthetic data only. Not a live NHS system.**

OpenMRS replaces a hand-built mock NHS PAS/EPR. It is a real clinical application with a
patient registry, a visit/encounter/observation data model, a REST API, and FHIR R4 — so
the bot genuinely interacts with a clinical system instead of faking it.

---

## 0. Prerequisites

- **Docker Desktop** running (WSL2 backend on Windows 11). Confirmed available.
- Allocate Docker **≥ 4 GB RAM** (6 GB comfortable). Settings → Resources.
  OpenMRS backend is a Tomcat/Java app + MariaDB; under 4 GB it boots slowly or stalls.
- **Port 80 free.** If IIS / another web server holds port 80, either stop it or change
  the gateway port mapping in `docker-compose.yml` from `"80:80"` to e.g. `"8080:80"`
  (then every URL below uses `http://localhost:8080/...`).
- ~5 GB free disk for images + volumes.

## 1. Start OpenMRS

From this folder (`openmrs-setup/`):

```powershell
docker compose pull          # ~1–3 GB download, first time only
docker compose up -d         # start all four services detached
docker compose ps            # see service status
```

**First boot is slow.** The backend runs Liquibase DB migrations and module startup on the
very first run — expect **3–10 minutes** before the app responds, even after the containers
show "Up". Watch progress:

```powershell
docker compose logs -f backend
```

Wait for a line indicating startup is complete (Tomcat "Server startup" / OpenMRS
"Spring context refreshed"). Then the SPA needs another minute to be served.

## 2. Verify it's up (acceptance evidence)

Open in a browser:

| What | URL |
|---|---|
| O3 SPA (modern UI) | http://localhost/openmrs/spa |
| Legacy admin UI | http://localhost/openmrs |
| REST self-check | http://localhost/openmrs/ws/rest/v1/session |

REST check from PowerShell (returns JSON with `"authenticated": false` before login):

```powershell
curl.exe http://localhost/openmrs/ws/rest/v1/session

# Authenticated call (Basic auth) — should return "authenticated": true:
curl.exe -u admin:Admin123 http://localhost/openmrs/ws/rest/v1/session
```

## 3. Login

- **Username:** `admin`
- **Password:** `Admin123`

On the O3 login you may be asked to pick a **Login Location** (e.g. *Outpatient Clinic*) —
pick any; this becomes the session location used on encounters.

## 4. Where the bot will work (map for later phases)

### Patient search
- **O3 SPA:** top-bar **Search** → searches by name or identifier; results list opens the
  patient chart. This is the screenshot-worthy, UI-automatable step.
- **REST:** `GET /ws/rest/v1/patient?q=<name-or-identifier>&v=full` — reliable, used by the
  bot for the actual match logic.

### Patient record updates / referral data
A referral is **not** a built-in OpenMRS object. We represent it with native structures:

```
Patient
  └─ Visit            (a contact episode)
       └─ Encounter   (encounterType = "Referral"  ← we create/configure this)
            ├─ Obs: Speciality / requested service
            ├─ Obs: Referral reason
            ├─ Obs: Urgency (Routine / Urgent / 2WW suspected cancer)
            ├─ Obs: Referrer name + org
            ├─ Obs: Suspected-cancer flag
            └─ Obs: Clinical summary (free text)
```

- **Create via REST:** `POST /ws/rest/v1/encounter` (with `obs[]`), under a `POST
  /ws/rest/v1/visit`. Verifiable by re-reading the encounter UUID.
- **Duplicate check via REST:** `GET /ws/rest/v1/encounter?patient=<uuid>&
  encounterType=<referral-uuid>&fromdate=...` then filter by speciality.
- Exact concept/encounter-type UUIDs and payload shapes are pinned in **Phase 6**.

### Recommended approach: **hybrid (REST-first)**
- **Writes → REST.** The O3 SPA is a React app; selector-based UI automation against it is
  fragile and slow. REST writes are reliable and verifiable.
- **Patient search/confirm → UI automation** for genuine browser-automation evidence and
  screenshots.
- We bring up both UIs in this phase, you eyeball them, and we **lock the UI-vs-REST split
  in Phase 6**. If the O3 SPA proves too flaky for even search, the **legacy 2.x UI**
  (`http://localhost/openmrs`) is plain-HTML and far friendlier to UiPath selectors.

## 5. Stop / reset

```powershell
docker compose stop          # pause, keep containers
docker compose down          # remove containers, KEEP data volumes
docker compose down -v       # remove containers AND volumes (full wipe — lose all data)
```

Use `down -v` only when you want a clean re-seed. Synthetic data, so no harm — but you'll
re-run Phase 2 seeding.

## 6. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Browser shows 502 / blank for several minutes | Backend still migrating. `docker compose logs -f backend` and wait. |
| Port 80 bind error on `up` | Another service owns port 80. Remap gateway to `"8080:80"`. |
| Backend container restarts in a loop | Too little RAM to Docker (<4 GB) or DB not ready. Raise RAM; `docker compose down && up -d`. |
| `curl ... /session` connection refused | Gateway/frontend not ready yet, or wrong port. |
| Login rejects admin/Admin123 | You re-seeded with a different DB, or backend not finished first-boot. |
| Want to start over cleanly | `docker compose down -v` then `up -d`. |

## 7. Phase 1 evidence to capture (screenshots)

1. `docker compose ps` showing all four services Up/healthy.
2. O3 SPA login screen + logged-in home (`/openmrs/spa`).
3. A patient search box (even empty is fine for now).
4. The REST `/session` JSON response (authenticated: true) in a browser/terminal.
5. (Optional) Legacy admin UI home (`/openmrs`).

Store these under `docs/testing/` or a `docs/evidence/phase1/` folder.
