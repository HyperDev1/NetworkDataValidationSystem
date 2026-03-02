---
phase: 02-secret-management
plan: 02
subsystem: secret-management
tags: [gcp, secret-manager, admob, oauth, cloud-run, bash]
dependency_graph:
  requires: [02-01-PLAN.md]
  provides: [scripts/setup-secrets.sh, src/fetchers/admob_fetcher.py ADMOB_TOKEN_JSON support]
  affects: [cloud-run-deployment, admob-oauth-flow]
tech_stack:
  added: []
  patterns: [env-var-json-token, cloud-local-branching, idempotent-secret-creation]
key_files:
  created: [scripts/setup-secrets.sh]
  modified: [src/fetchers/admob_fetcher.py]
decisions:
  - "ADMOB_TOKEN_JSON env var check added before file-based check — Cloud Run path takes priority, local dev unchanged"
  - "from_authorized_user_info (dict) used for env var path, from_authorized_user_file (file) for local path"
  - "_save_token early-returns when ADMOB_TOKEN_JSON is set — Cloud Run instances are ephemeral, no file write needed"
  - "setup-secrets.sh skips secrets not in env rather than failing — idempotent, partial setup supported"
  - "APPLOVIN_PACKAGE_NAME included in setup-secrets.sh (was in env var list from 02-01)"
metrics:
  duration: "~2 min"
  completed_date: "2026-03-02"
  tasks_completed: 2
  files_changed: 2
---

# Phase 2 Plan 02: Secret Manager Setup Script and AdMob Cloud Run Token Support Summary

**One-liner:** AdmobFetcher reads OAuth token from ADMOB_TOKEN_JSON env var in Cloud Run (JSON string, no file write), falls back to file for local dev; setup-secrets.sh creates all 28 GCP secrets and prints the Cloud Run deploy command.

## What Was Built

### Task 1: AdmobFetcher ADMOB_TOKEN_JSON support (commit: a4e0b5d)

Modified `src/fetchers/admob_fetcher.py` — `_authenticate_oauth()` and `_save_token()` only. `__init__` signature unchanged.

**_authenticate_oauth() changes:**
- Added Cloud Run path at the very start: reads `ADMOB_TOKEN_JSON` env var, parses JSON string with `json.loads()`, loads credentials using `Credentials.from_authorized_user_info(token_data, self.SCOPES)`
- Local dev path (file-based) unchanged — runs when `ADMOB_TOKEN_JSON` is not set
- Token refresh logic works for both paths (in-memory after refresh in Cloud Run)
- OAuth browser flow still available for local dev when credentials file provided

**_save_token() changes:**
- Early return when `ADMOB_TOKEN_JSON` env var is present — Cloud Run instances are ephemeral, no file system write attempted
- File write path unchanged for local dev

### Task 2: scripts/setup-secrets.sh (commit: 081309f)

Created `scripts/setup-secrets.sh` as a reproducible operator runbook:
- Validates prerequisites: `PROJECT_ID` env var set, `gcloud` CLI available
- `create_or_update_secret()` helper: creates secret if new, adds version if exists (idempotent)
- Covers all 28 secrets across 12 networks: AppLovin, Mintegral, Unity Ads, AdMob, Meta, Moloco, BidMachine, Liftoff, DT Exchange, Pangle, IronSource, InMobi, plus Slack and GCP
- Secrets not set in environment are skipped with a `SKIP:` warning (partial setup supported)
- Prints the full `gcloud run jobs deploy --set-secrets` command at completion

## Deviations from Plan

### Auto-fixed Issues

None.

**Additional:** The plan's secret list referenced 28 secrets but the `--set-secrets` snippet example in the plan omitted `APPLOVIN_PACKAGE_NAME`. Added it to both the creation section and deploy snippet to match the env var list from 02-01 context.

## Success Criteria Verification

| Criterion | Status |
|-----------|--------|
| AdmobFetcher reads ADMOB_TOKEN_JSON for Cloud Run | PASS |
| AdmobFetcher falls back to file for local dev | PASS |
| Token refresh in Cloud Run is in-memory only (no file write) | PASS |
| setup-secrets.sh creates all Secret Manager secrets | PASS |
| setup-secrets.sh prints gcloud run deploy --set-secrets command | PASS |
| Both files are syntactically valid | PASS |

## Self-Check: PASSED

- src/fetchers/admob_fetcher.py: FOUND
- scripts/setup-secrets.sh: FOUND
- 02-02-SUMMARY.md: FOUND
- Commit a4e0b5d (Task 1): FOUND
- Commit 081309f (Task 2): FOUND
