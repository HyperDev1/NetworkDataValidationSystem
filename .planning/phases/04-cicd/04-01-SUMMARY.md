---
phase: 04-cicd
plan: 01
subsystem: infra
tags: [gcloud, artifact-registry, workload-identity, github-actions, oidc, iam, docker]

# Dependency graph
requires:
  - phase: 01-containerization
    provides: Dockerfile for Docker image builds
  - phase: 03-scheduling
    provides: SA naming convention (network-data-*-sa pattern)
provides:
  - scripts/setup-cicd.sh — one-shot GCP provisioning for keyless GitHub Actions auth
  - Artifact Registry repository (network-data-validation, Docker, us-central1)
  - Workload Identity Pool (github-actions-pool) + OIDC Provider (github-provider)
  - CI/CD service account (network-data-cicd-sa) with 3 minimum IAM roles
  - GitHub secrets values: WIF_PROVIDER, WIF_SERVICE_ACCOUNT, GCP_PROJECT_ID
affects: [04-02-workflow, 04-03-deploy]

# Tech tracking
tech-stack:
  added: [gcloud iam workload-identity-pools, gcloud artifacts repositories]
  patterns: [check-before-create idempotency, principalSet WIF binding, setup-*.sh operator script convention]

key-files:
  created: [scripts/setup-cicd.sh]
  modified: []

key-decisions:
  - "Workload Identity Federation (keyless) — no JSON key stored, GitHub OIDC token exchanged for short-lived GCP access token"
  - "principalSet (not principal) binding — allows any workflow from the repo to authenticate, not just specific actors/branches"
  - "roles/iam.serviceAccountTokenCreator self-binding on the SA — required for WIF impersonation chain to complete"
  - "Three env vars required (PROJECT_ID, GCP_PROJECT_NUMBER, GITHUB_REPO) — all needed to construct WIF resource paths"
  - "artifactregistry.googleapis.com + iamcredentials.googleapis.com APIs enabled idempotently — Artifact Registry for image storage, IAM Credentials for WIF token exchange"

patterns-established:
  - "setup-cicd.sh style: header block + set -euo pipefail + prereq checks + section headers + check-before-create + final summary block"
  - "Inline WHY comments for complex GCP setup (WIF especially) — makes script approachable for operators not expert in WIF"

requirements-completed: [CICD-01, CICD-02, CICD-03]

# Metrics
duration: 2min
completed: 2026-03-02
---

# Phase 4 Plan 01: CI/CD Setup Script Summary

**One-shot `setup-cicd.sh` that provisions Artifact Registry + Workload Identity Federation for keyless GitHub Actions auth to GCP without stored JSON keys**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-02T12:10:29Z
- **Completed:** 2026-03-02T12:11:49Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Created `scripts/setup-cicd.sh` — idempotent operator script covering all GCP infrastructure for CI/CD
- All 6 resource creation sections follow check-before-create pattern (safe to re-run)
- Inline WHY comments explain Workload Identity Federation for non-WIF-expert operators
- Final section prints exact values to paste as GitHub repository secrets

## Task Commits

Each task was committed atomically:

1. **Task 1: Create scripts/setup-cicd.sh** - `b7a127b` (feat)

**Plan metadata:** _(docs commit follows)_

## Files Created/Modified
- `scripts/setup-cicd.sh` - One-shot GCP provisioning: Artifact Registry + WIF Pool/Provider + CI/CD SA + IAM bindings

## Decisions Made
- Used `principalSet://` (not `principal://`) for WIF binding — matches all tokens from the repo regardless of branch/actor, which is the correct scope for a CI/CD SA
- `roles/iam.serviceAccountTokenCreator` granted as a self-binding on the SA — required for the WIF impersonation chain (GitHub OIDC -> WIF exchange -> SA token) to work
- Required `GCP_PROJECT_NUMBER` as a separate env var (not derived from `PROJECT_ID`) — the project number is required to construct the WIF resource path and `gcloud projects describe` would add a network call that complicates the prereq check
- API enable steps use the same filter pattern from `setup-scheduler.sh` — consistent with project conventions

## Deviations from Plan

None — plan executed exactly as written. The script was created with all specified sections, check-before-create pattern, and matches setup-secrets.sh/setup-scheduler.sh style conventions.

## Issues Encountered

None.

## User Setup Required

After running `setup-cicd.sh`, the operator must add 3 GitHub repository secrets:
- `WIF_PROVIDER` — printed by the script at completion
- `WIF_SERVICE_ACCOUNT` — printed by the script at completion
- `GCP_PROJECT_ID` — printed by the script at completion

(Settings -> Secrets and variables -> Actions -> New repository secret)

## Next Phase Readiness
- GCP infrastructure for CI/CD is fully provisioned — ready for Phase 04-02 (GitHub Actions workflow file)
- Image path `us-central1-docker.pkg.dev/{PROJECT_ID}/network-data-validation/app` is established and consistent with 04-CONTEXT.md
- No blockers for next plan

---
*Phase: 04-cicd*
*Completed: 2026-03-02*
