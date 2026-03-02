#!/usr/bin/env bash
# setup-scheduler.sh — Provision Cloud Scheduler + OIDC auth for Network Data Validation System
#
# Usage:
#   1. Set PROJECT_ID: export PROJECT_ID=your-gcp-project-id
#   2. Set CLOUD_RUN_SERVICE_URL: export CLOUD_RUN_SERVICE_URL=https://network-data-validation-xxxxx-uc.a.run.app
#   3. Run: bash scripts/setup-scheduler.sh
#
# What this script does:
#   - Creates a dedicated service account for Cloud Scheduler (network-data-scheduler-sa)
#   - Grants roles/run.invoker to the service account on the Cloud Run service
#   - Creates/updates a Cloud Scheduler job (network-data-validation-scheduler)
#     Schedule: 0 */3 * * * (every 3 hours UTC — 00:00, 03:00, 06:00, 09:00, 12:00, 15:00, 18:00, 21:00)
#   - Retry policy: 5 attempts, exponential backoff (1m -> 2m -> 4m -> 8m -> 16m)
#   - Auth: OIDC token from service account (Cloud Run is NOT publicly accessible)

set -euo pipefail

# --- Prerequisites ---

if [ -z "${PROJECT_ID:-}" ]; then
  echo "ERROR: PROJECT_ID env var is required. Export it first:"
  echo "  export PROJECT_ID=your-gcp-project-id"
  exit 1
fi

if [ -z "${CLOUD_RUN_SERVICE_URL:-}" ]; then
  echo "ERROR: CLOUD_RUN_SERVICE_URL env var is required. Export it first:"
  echo "  export CLOUD_RUN_SERVICE_URL=https://network-data-validation-xxxxx-uc.a.run.app"
  exit 1
fi

if ! command -v gcloud &>/dev/null; then
  echo "ERROR: gcloud CLI not found. Install Google Cloud SDK."
  exit 1
fi

echo "Setting up Cloud Scheduler for project: $PROJECT_ID"
gcloud config set project "$PROJECT_ID"

# --- Enable Cloud Scheduler API ---

echo ""
echo "=== Cloud Scheduler API ==="
if gcloud services list --enabled --filter="name:cloudscheduler.googleapis.com" --format="value(name)" --project="$PROJECT_ID" 2>/dev/null | grep -q cloudscheduler; then
  echo "  Cloud Scheduler API already enabled — skipping"
else
  echo "  Enabling Cloud Scheduler API..."
  gcloud services enable cloudscheduler.googleapis.com --project="$PROJECT_ID"
fi

# --- Service Account ---

echo ""
echo "=== Service Account ==="
SA_EMAIL="network-data-scheduler-sa@${PROJECT_ID}.iam.gserviceaccount.com"

if gcloud iam service-accounts describe "$SA_EMAIL" --project="$PROJECT_ID" &>/dev/null; then
  echo "  Service account already exists: $SA_EMAIL — skipping"
else
  echo "  Creating service account: network-data-scheduler-sa"
  gcloud iam service-accounts create network-data-scheduler-sa \
    --display-name="Network Data Validation Scheduler" \
    --project="$PROJECT_ID"
fi

# --- IAM Binding ---

echo ""
echo "=== IAM Binding ==="
echo "  Granting roles/run.invoker to $SA_EMAIL on Cloud Run service..."
# IAM bindings are idempotent — gcloud silently skips if binding already exists
gcloud run services add-iam-policy-binding network-data-validation \
  --region=us-central1 \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/run.invoker" \
  --project="$PROJECT_ID"

# --- Cloud Scheduler Job ---

echo ""
echo "=== Cloud Scheduler Job ==="
JOB_NAME="network-data-validation-scheduler"

if gcloud scheduler jobs describe "$JOB_NAME" --location=us-central1 --project="$PROJECT_ID" &>/dev/null; then
  echo "  Updating existing Cloud Scheduler job: $JOB_NAME"
  gcloud scheduler jobs update http "$JOB_NAME" \
    --location=us-central1 \
    --schedule="0 */3 * * *" \
    --uri="${CLOUD_RUN_SERVICE_URL}/validate" \
    --http-method=POST \
    --oidc-service-account-email="$SA_EMAIL" \
    --oidc-token-audience="${CLOUD_RUN_SERVICE_URL}" \
    --max-retry-attempts=5 \
    --min-backoff=1m \
    --max-backoff=16m \
    --attempt-deadline=30m \
    --time-zone=UTC \
    --project="$PROJECT_ID"
else
  echo "  Creating Cloud Scheduler job: $JOB_NAME"
  gcloud scheduler jobs create http "$JOB_NAME" \
    --location=us-central1 \
    --schedule="0 */3 * * *" \
    --uri="${CLOUD_RUN_SERVICE_URL}/validate" \
    --http-method=POST \
    --oidc-service-account-email="$SA_EMAIL" \
    --oidc-token-audience="${CLOUD_RUN_SERVICE_URL}" \
    --max-retry-attempts=5 \
    --min-backoff=1m \
    --max-backoff=16m \
    --attempt-deadline=30m \
    --time-zone=UTC \
    --project="$PROJECT_ID"
fi

# --- Cloud Run OIDC lock-down reminder ---
# The Cloud Run service must be deployed with --no-allow-unauthenticated to prevent
# public access. Only the scheduler service account (via OIDC) should be able to invoke it.

echo ""
echo "IMPORTANT: Ensure Cloud Run service is deployed with --no-allow-unauthenticated"
echo "Add this flag to the gcloud run deploy command in setup-secrets.sh:"
echo "  --no-allow-unauthenticated"

# --- Verification snippet ---

echo ""
echo "==================================================================="
echo "Cloud Scheduler setup complete."
echo ""
echo "Verify setup:"
echo "  gcloud scheduler jobs describe $JOB_NAME --location=us-central1"
echo ""
echo "Manual trigger (test run):"
echo "  gcloud scheduler jobs run $JOB_NAME --location=us-central1"
echo "==================================================================="
