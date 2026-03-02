---
phase: 04-cicd
plan: "02"
subsystem: infra
tags: [github-actions, docker, artifact-registry, cloud-run, workload-identity, cicd]

# Dependency graph
requires:
  - phase: 04-cicd/04-01
    provides: setup-cicd.sh that provisions Artifact Registry, Workload Identity Pool/Provider, and SA IAM bindings

provides:
  - .github/workflows/deploy.yml — GitHub Actions CI/CD pipeline automating build, push, and deploy on main branch pushes
  - build-check job for PR Dockerfile validation before merge

affects:
  - future phases: any code change merged to main now automatically ships to Cloud Run

# Tech tracking
tech-stack:
  added:
    - google-github-actions/auth@v2 (Workload Identity Federation OIDC)
    - google-github-actions/deploy-cloudrun@v2
    - docker/build-push-action@v5
    - docker/setup-buildx-action@v3
    - actions/cache@v4 (Docker layer caching)
  patterns:
    - Keyless GCP auth from GitHub Actions via Workload Identity Federation (OIDC token exchange, no stored JSON key)
    - Dual image tagging: sha-{commit_sha} for traceability + latest for production pointer
    - Three-job workflow: build-and-push (main push) + deploy (main push, needs build-and-push) + build-check (PR only)
    - Docker layer cache keyed on requirements.txt + Pipfile.lock with cache bloat prevention via mv pattern

key-files:
  created:
    - .github/workflows/deploy.yml
  modified: []

key-decisions:
  - "build-and-push and deploy jobs gated with if: github.event_name == 'push' — ensures PRs never trigger production push or deploy"
  - "build-check on PRs uses type=gha cache (simpler, ephemeral) while main push uses type=local (persistent cache volume with mv anti-bloat pattern)"
  - "deploy job re-authenticates with WIF independently rather than sharing token from build-and-push — jobs run in different runners, tokens are not transferable"
  - "outputs: image declared on build-and-push job for traceability even though deploy job re-constructs the tag from env.IMAGE + github.sha"

patterns-established:
  - "WIF auth pattern: id-token: write permission + google-github-actions/auth@v2 with WIF_PROVIDER + WIF_SERVICE_ACCOUNT secrets"
  - "Docker cache pattern: setup-buildx + actions/cache on /tmp/.buildx-cache + mv /tmp/.buildx-cache-new /tmp/.buildx-cache after build"

requirements-completed: [CICD-01, CICD-02, CICD-03]

# Metrics
duration: 1min
completed: "2026-03-02"
---

# Phase 4 Plan 02: CI/CD Pipeline (deploy.yml) Summary

**GitHub Actions workflow automating build -> push to Artifact Registry (sha + latest tags) -> Cloud Run deploy on every main push; PR-only build-check job validates Dockerfile without push using WIF keyless auth throughout**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-03-02T12:13:45Z
- **Completed:** 2026-03-02T12:14:51Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Created `.github/workflows/deploy.yml` with three jobs covering the full CI/CD lifecycle
- main push path: build-and-push (WIF auth, Docker build, push with sha + latest tags, layer cache) then deploy (WIF auth, deploy-cloudrun with --no-allow-unauthenticated)
- PR path: build-check (WIF auth, build only, no push, GitHub Actions cache) for fast merge-gate feedback
- No hardcoded credentials or project IDs — all sensitive values via GitHub secrets (WIF_PROVIDER, WIF_SERVICE_ACCOUNT, GCP_PROJECT_ID)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create .github/workflows/deploy.yml** - `a0ecb53` (feat)

## Files Created/Modified
- `.github/workflows/deploy.yml` — GitHub Actions CI/CD pipeline (141 lines): triggers on main push and PRs, implements build-and-push, deploy, and build-check jobs

## Decisions Made
- build-and-push and deploy jobs gated with `if: github.event_name == 'push'` — PRs never trigger production push or deploy
- build-check on PRs uses `type=gha` cache (simpler, ephemeral) while main push uses `type=local` with the mv anti-bloat pattern (persistent runner cache)
- deploy job re-authenticates with WIF independently — jobs run in different runners, OIDC tokens are not transferable between jobs
- `outputs: image` declared on build-and-push for traceability even though deploy job reconstructs the tag from `env.IMAGE + github.sha`

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
- pyyaml not installed in system Python; installed it to run YAML validation. Validation passed.

## User Setup Required
None — GCP provisioning is handled by `scripts/setup-cicd.sh` (from plan 04-01). GitHub secrets (WIF_PROVIDER, WIF_SERVICE_ACCOUNT, GCP_PROJECT_ID) must be set in the repository before the first push to main, but this is documented in the workflow header comment.

## Next Phase Readiness
- CI/CD pipeline is complete: any `git push origin main` now automatically builds, pushes, and deploys
- Phase 4.1 (dynamic game configuration system) can proceed — code changes will ship automatically via this pipeline
- Prerequisite: GitHub secrets must be configured and `scripts/setup-cicd.sh` must have been run at least once

---
*Phase: 04-cicd*
*Completed: 2026-03-02*

## Self-Check: PASSED

- FOUND: .github/workflows/deploy.yml
- FOUND: .planning/phases/04-cicd/04-02-SUMMARY.md
- FOUND commit: a0ecb53
