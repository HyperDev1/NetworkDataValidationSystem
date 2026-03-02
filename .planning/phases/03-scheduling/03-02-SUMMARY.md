---
phase: 03-scheduling
plan: 02
subsystem: infra
tags: [gcloud, cloud-scheduler, oidc, service-account, iam, bash, idempotent]

# Dependency graph
requires:
  - phase: 02-secret-management
    provides: setup-secrets.sh style/pattern reference for bash script conventions
  - phase: 03-scheduling
    provides: 03-01 /validate endpoint returning 500 on partial failure (Cloud Scheduler retry target)
provides:
  - scripts/setup-scheduler.sh: one-shot idempotent provisioning of Cloud Scheduler + OIDC auth
  - Cloud Scheduler job (network-data-validation-scheduler) firing POST /validate every 3 hours UTC
  - Dedicated service account (network-data-scheduler-sa) with roles/run.invoker on Cloud Run
  - 5-retry exponential backoff policy (1m -> 2m -> 4m -> 8m -> 16m)
affects:
  - 04-deployment
  - Any phase that deploys to Cloud Run (must use --no-allow-unauthenticated)

# Tech tracking
tech-stack:
  added: [gcloud scheduler jobs, gcloud iam service-accounts, OIDC token auth for Cloud Run]
  patterns:
    - Check-before-create idempotency for gcloud resources (describe || create)
    - Check-before-update for scheduler job (describe && update || create)
    - IAM bindings applied without check (gcloud handles idempotency natively)
    - Cloud Scheduler API auto-enable via gcloud services enable

key-files:
  created:
    - scripts/setup-scheduler.sh
  modified: []

key-decisions:
  - "Job name: network-data-validation-scheduler — matches project naming convention"
  - "Service account: network-data-scheduler-sa@${PROJECT_ID}.iam.gserviceaccount.com — dedicated SA, not reusing existing"
  - "OIDC token audience = CLOUD_RUN_SERVICE_URL (not /validate path) — standard audience for Cloud Run OIDC"
  - "attempt-deadline=30m — allows full validation run to complete before Cloud Scheduler abandons the attempt"
  - "CLOUD_RUN_SERVICE_URL as required env var — avoids hardcoding project-specific URL in script"

patterns-established:
  - "Idempotent gcloud bash scripts: describe-before-create for SA and scheduler job, IAM binding applied unconditionally"
  - "Script header with Usage + What-this-does section following setup-secrets.sh style"
  - "set -euo pipefail + prerequisite checks (env vars + gcloud CLI) before any side effects"

requirements-completed: [SCHED-01, SCHED-02]

# Metrics
duration: ~10min (including human verification checkpoint)
completed: 2026-03-02
---

# Phase 3 Plan 02: Scheduling Infrastructure Summary

**Idempotent Cloud Scheduler provisioning script with OIDC service account, roles/run.invoker IAM binding, 3-hour cron, and 5-retry exponential backoff — ready for operator `bash scripts/setup-scheduler.sh`**

## Performance

- **Duration:** ~10 min (including human verification checkpoint)
- **Started:** 2026-03-02T11:36:37Z
- **Completed:** 2026-03-02T11:40:00Z
- **Tasks:** 2 (1 auto + 1 checkpoint:human-verify)
- **Files modified:** 1

## Accomplishments

- Created `scripts/setup-scheduler.sh` — one-shot idempotent script that provisions all Cloud Scheduler infrastructure
- Cloud Scheduler job configured: POST `/validate` every 3 hours UTC (`0 */3 * * *`), OIDC auth, 5-retry backoff
- Service account `network-data-scheduler-sa` with `roles/run.invoker` binding on Cloud Run service
- Human review checkpoint passed — operator confirmed script is correct and production-ready

## Task Commits

Each task was committed atomically:

1. **Task 1: Create setup-scheduler.sh** - `045591b` (feat)
2. **Task 2: Verify setup-scheduler.sh content and GCP infrastructure** - `checkpoint:human-verify` — approved by user

**Plan metadata:** (docs commit — created with this SUMMARY)

## Files Created/Modified

- `scripts/setup-scheduler.sh` — Full Cloud Scheduler provisioning script: prerequisites check, Cloud Scheduler API enable, service account create (idempotent), IAM binding (roles/run.invoker), scheduler job create/update (idempotent), OIDC lock-down reminder, verification snippet

## Decisions Made

- OIDC token audience set to `CLOUD_RUN_SERVICE_URL` (not the `/validate` path) — standard Cloud Run OIDC audience convention
- `--attempt-deadline=30m` added to allow full validation runs to complete before Cloud Scheduler times out
- `CLOUD_RUN_SERVICE_URL` as required env var at script invocation time — avoids hardcoding project-specific URL, keeps script portable across environments
- Scheduler job uses check-before-update pattern (not check-before-skip) so re-running always brings job to desired state even if config drifted

## Deviations from Plan

None — plan executed exactly as written. Script implements all specified sections (prerequisites, service account, IAM binding, scheduler job with create/update paths, lock-down reminder, verification snippet).

## Issues Encountered

None.

## User Setup Required

Before running `scripts/setup-scheduler.sh`, the operator must:

1. Set `PROJECT_ID`: `export PROJECT_ID=your-gcp-project-id`
2. Set `CLOUD_RUN_SERVICE_URL`: `export CLOUD_RUN_SERVICE_URL=https://network-data-validation-xxxxx-uc.a.run.app`
3. Ensure Cloud Run service is deployed with `--no-allow-unauthenticated`
4. Run: `bash scripts/setup-scheduler.sh`

Verification after run:
```bash
gcloud scheduler jobs describe network-data-validation-scheduler --location=us-central1
```

Manual trigger (test run):
```bash
gcloud scheduler jobs run network-data-validation-scheduler --location=us-central1
```

## Next Phase Readiness

- Phase 3 scheduling infrastructure is complete: `/validate` returns correct HTTP codes (03-01) and Cloud Scheduler is provisioned to call it every 3 hours via OIDC (03-02)
- Phase 4 (deployment) can now include `--no-allow-unauthenticated` in Cloud Run deploy commands, knowing the scheduler SA has invoker access
- No blockers for Phase 4

---
*Phase: 03-scheduling*
*Completed: 2026-03-02*
