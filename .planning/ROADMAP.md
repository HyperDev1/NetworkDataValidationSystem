# Roadmap: Network Data Validation System

## Milestones

- ✅ **v1.0.0 Pre-GSD** - Phases 0 (shipped before GSD adoption)
- 🚧 **v1.0.1 Google Cloud Run** - Phases 1-4 (in progress)

## Overview

The existing validation pipeline runs locally. This milestone containerizes it, moves secrets to GCP Secret Manager, wires Cloud Scheduler for automatic daily execution, and adds a CI/CD pipeline so every push to main deploys automatically. When complete, the system runs entirely in the cloud with no manual intervention required.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

<details>
<summary>✅ v1.0.0 Pre-GSD (Phase 0) - SHIPPED before GSD adoption</summary>

**What shipped:**
- Async parallel data fetching from 12 ad networks
- AppLovin MAX baseline comparison
- Revenue/impressions/eCPM delta calculations
- Slack notifications with threshold filtering
- GCS Parquet export with Hive partitioning
- Scheduled mode and service mode
- Graceful degradation for failed networks

</details>

### 🚧 v1.0.1 Google Cloud Run (In Progress)

**Milestone Goal:** Pipeline runs fully in the cloud — containerized, secrets in GCP Secret Manager, triggered by Cloud Scheduler, deployed automatically via GitHub Actions.

- [x] **Phase 1: Containerization** - Production-ready Docker image that builds and runs locally
- [x] **Phase 2: Secret Management** - All credentials moved to GCP Secret Manager, config reads from env (completed 2026-03-02)
- [x] **Phase 3: Scheduling** - Cloud Run triggered by Cloud Scheduler on daily schedule (completed 2026-03-02)
- [ ] **Phase 4: CI/CD** - GitHub Actions builds, pushes, and deploys on every main branch push

## Phase Details

### Phase 1: Containerization
**Goal**: Production-ready container image exists and runs correctly in local environment
**Depends on**: Nothing (first phase)
**Requirements**: CONT-01, CONT-02, CONT-03, CONT-04
**Success Criteria** (what must be TRUE):
  1. `docker build` completes without error using the multi-stage Dockerfile
  2. `docker run` starts the container and the application runs validation
  3. Container responds to HTTP health check endpoint (returns 200)
  4. Sensitive files (credentials/, config.yaml, .git) are absent from the built image
**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md — Flask HTTP server, multi-stage Dockerfile, .dockerignore
- [x] 01-02-PLAN.md — docker-compose.yml and local container verification

### Phase 2: Secret Management
**Goal**: All API credentials live in GCP Secret Manager and the application reads them without touching config.yaml at runtime
**Depends on**: Phase 1
**Requirements**: SEC-01, SEC-02, SEC-03, SEC-04
**Success Criteria** (what must be TRUE):
  1. config.yaml no longer contains any API keys, tokens, or OAuth credentials
  2. Application starts and runs validation when secrets are injected as environment variables
  3. Application falls back to config.yaml values when environment variables are absent (local dev still works)
  4. AdMob OAuth refresh token is stored in Secret Manager and read by the container at runtime
**Plans**: 3 plans

Plans:
- [x] 02-01-PLAN.md — Config env var overrides and _merge_env_vars
- [x] 02-02-PLAN.md — Secret Manager setup script and AdMob Cloud Run token support
- [x] 02-03-PLAN.md — ADMOB_OAUTH_CREDENTIALS_PATH gap closure in setup-secrets.sh

### Phase 3: Scheduling
**Goal**: Cloud Run executes the validation pipeline daily without any manual trigger
**Depends on**: Phase 2
**Requirements**: SCHED-01, SCHED-02
**Success Criteria** (what must be TRUE):
  1. Cloud Scheduler fires an HTTP request to Cloud Run at the configured daily time
  2. Cloud Run receives the request, runs validation end-to-end, and returns an HTTP response indicating success or failure
**Plans**: 2 plans

Plans:
- [x] 03-01-PLAN.md — Fix /validate response codes (500 on partial network failure, TDD)
- [x] 03-02-PLAN.md — setup-scheduler.sh: service account, OIDC, Cloud Scheduler job provisioning

### Phase 4: CI/CD
**Goal**: Pushing to main branch automatically builds, publishes, and deploys the latest image to Cloud Run
**Depends on**: Phase 3
**Requirements**: CICD-01, CICD-02, CICD-03
**Success Criteria** (what must be TRUE):
  1. A push to main triggers the GitHub Actions workflow and builds a new Docker image
  2. The built image is pushed to Google Artifact Registry with a new tag
  3. Cloud Run service is updated to the new image automatically after the push completes
**Plans**: 3 plans

Plans:
- [ ] 04-01-PLAN.md — scripts/setup-cicd.sh: Artifact Registry, Workload Identity, SA, IAM bindings
- [ ] 04-02-PLAN.md — .github/workflows/deploy.yml: build+push+deploy on main, build-check on PR
- [ ] 04-03-PLAN.md — GCP provisioning, GitHub secrets setup, end-to-end pipeline verification

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Containerization | v1.0.1 | 2/2 | Complete | 2026-03-02 |
| 2. Secret Management | v1.0.1 | Complete    | 2026-03-02 | 2026-03-02 |
| 3. Scheduling | v1.0.1 | 2/2 | Complete | 2026-03-02 |
| 4. CI/CD | 2/3 | In Progress|  | - |

### Phase 04.1: Dynamic game configuration system for adding and removing games from validation reports (INSERTED)

**Goal:** [Urgent work - to be planned]
**Requirements**: TBD
**Depends on:** Phase 4
**Plans:** 2/3 plans executed

Plans:
- [ ] TBD (run /gsd:plan-phase 04.1 to break down)
