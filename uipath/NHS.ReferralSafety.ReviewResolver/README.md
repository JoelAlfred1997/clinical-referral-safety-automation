# NHS.ReferralSafety.ReviewResolver (Phase 9)

A small UiPath **Process** that closes the human-in-the-loop loop: it asks the
review service to apply the clinician decisions recorded against the referrals
the Phase 8 bot routed to human review.

It is deliberately thin — the same service-oriented pattern as the Phase 8
performer (which POSTs to the extraction / decision / writeback services). The
review store, the state machine and the OpenMRS create/verify live in the
`services/review-service` Python service; this process is the **bot trigger** that
re-reads the decisions and reports the outcome.

## Main.xaml

1. `POST {resolveUrl}` (default `http://localhost:8092/resolve`) via **HTTP Request**.
2. Guard: a non-200 response → `Throw Exception` (system fault — service down).
3. **Deserialize JSON** the summary.
4. Log: `Resolved N review(s): C created in OpenMRS, R rejected (no record), F failed.`
5. Guard: `failed > 0` → `Throw Exception` (a resolution hit a system fault; see the audit log).

For each decided review the service does the real work:
`APPROVE`/`AMEND` → create the referral in OpenMRS (writeback `:8091`, verified by
re-read); `REJECT` → no record. Every outcome appends an audit row. The pass is
idempotent: already-resolved reviews are skipped and the OpenMRS write is keyed on
`REF-NNN`, so a re-run creates no duplicates.

## Run

```bash
# review service running on :8092 (POST /resolve), writeback :8091, OpenMRS up
export PATH="/c/Program Files/dotnet:$PATH"
uip rpa validate --file-path Main.xaml
uip rpa run --file-path Main.xaml            # first run: applies the decisions
uip rpa run --file-path Main.xaml --skip-build   # re-run: resolves 0 (idempotent)
```

Dependencies: `UiPath.System.Activities`, `UiPath.WebAPI.Activities` (HTTP Request
+ Deserialize JSON). Windows / VB. **Synthetic data only.**
