#!/usr/bin/env bash
# setup-cicd.sh — Provision GCP infrastructure for keyless GitHub Actions CI/CD
#
# Usage:
#   1. Set PROJECT_ID:          export PROJECT_ID=your-gcp-project-id
#   2. Set GCP_PROJECT_NUMBER:  export GCP_PROJECT_NUMBER=123456789012
#   3. Set GITHUB_REPO:         export GITHUB_REPO=your-org/your-repo
#   4. Run:                     bash scripts/setup-cicd.sh
#
# What this script does:
#   - Enables required GCP APIs (Artifact Registry, IAM Credentials)
#   - Creates an Artifact Registry repository for Docker images (network-data-validation)
#   - Creates a dedicated CI/CD service account (network-data-cicd-sa) with minimal roles:
#       roles/artifactregistry.writer   — push Docker images
#       roles/run.admin                 — deploy Cloud Run services
#       roles/iam.serviceAccountTokenCreator — allow the SA to mint tokens (needed for
#                                              Workload Identity impersonation)
#   - Creates a Workload Identity Pool + GitHub OIDC Provider
#     (Workload Identity Federation lets GitHub Actions authenticate to GCP without
#      storing any long-lived JSON key — a short-lived OIDC token is exchanged for
#      a GCP access token automatically in each workflow run)
#   - Binds the Workload Identity principal for your GitHub repo to the CI/CD SA
#
# After running this script once, add the printed values as GitHub repository secrets.
# Every subsequent push to main will authenticate automatically — no stored credentials.

set -euo pipefail

# --- Prerequisites ---

if [ -z "${PROJECT_ID:-}" ]; then
  echo "ERROR: PROJECT_ID env var is required. Export it first:"
  echo "  export PROJECT_ID=your-gcp-project-id"
  exit 1
fi

if [ -z "${GCP_PROJECT_NUMBER:-}" ]; then
  echo "ERROR: GCP_PROJECT_NUMBER env var is required. Export it first:"
  echo "  export GCP_PROJECT_NUMBER=123456789012"
  echo "  (Find it: gcloud projects describe \$PROJECT_ID --format='value(projectNumber)')"
  exit 1
fi

if [ -z "${GITHUB_REPO:-}" ]; then
  echo "ERROR: GITHUB_REPO env var is required. Export it first:"
  echo "  export GITHUB_REPO=your-org/your-repo  (e.g. acme/network-data-validation)"
  exit 1
fi

if ! command -v gcloud &>/dev/null; then
  echo "ERROR: gcloud CLI not found. Install Google Cloud SDK."
  exit 1
fi

echo "Setting up CI/CD infrastructure for project: $PROJECT_ID"
echo "  GitHub repo:      $GITHUB_REPO"
echo "  Project number:   $GCP_PROJECT_NUMBER"
gcloud config set project "$PROJECT_ID"

# --- Enable APIs ---

echo ""
echo "=== Enable APIs ==="

# Artifact Registry API — needed to create and push images to the registry
if gcloud services list --enabled --filter="name:artifactregistry.googleapis.com" --format="value(name)" --project="$PROJECT_ID" 2>/dev/null | grep -q artifactregistry; then
  echo "  Artifact Registry API already enabled — skipping"
else
  echo "  Enabling Artifact Registry API..."
  gcloud services enable artifactregistry.googleapis.com --project="$PROJECT_ID"
fi

# IAM Credentials API — needed by Workload Identity Federation to generate short-lived tokens
if gcloud services list --enabled --filter="name:iamcredentials.googleapis.com" --format="value(name)" --project="$PROJECT_ID" 2>/dev/null | grep -q iamcredentials; then
  echo "  IAM Credentials API already enabled — skipping"
else
  echo "  Enabling IAM Credentials API..."
  gcloud services enable iamcredentials.googleapis.com --project="$PROJECT_ID"
fi

# --- Artifact Registry ---

echo ""
echo "=== Artifact Registry ==="
REGISTRY_REPO="network-data-validation"

if gcloud artifacts repositories describe "$REGISTRY_REPO" \
    --location=us-central1 \
    --project="$PROJECT_ID" &>/dev/null; then
  echo "  Repository already exists: $REGISTRY_REPO — skipping"
else
  echo "  Creating Artifact Registry repository: $REGISTRY_REPO"
  gcloud artifacts repositories create "$REGISTRY_REPO" \
    --repository-format=DOCKER \
    --location=us-central1 \
    --description="Network Data Validation System Docker images" \
    --project="$PROJECT_ID"
fi

# --- CI/CD Service Account ---

echo ""
echo "=== CI/CD Service Account ==="
SA_NAME="network-data-cicd-sa"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

if gcloud iam service-accounts describe "$SA_EMAIL" --project="$PROJECT_ID" &>/dev/null; then
  echo "  Service account already exists: $SA_EMAIL — skipping creation"
else
  echo "  Creating service account: $SA_NAME"
  gcloud iam service-accounts create "$SA_NAME" \
    --display-name="Network Data CI/CD Service Account" \
    --project="$PROJECT_ID"
fi

# Grant project-level roles — these are always applied (IAM bindings are idempotent)
echo "  Granting roles/artifactregistry.writer on project (push Docker images)..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/artifactregistry.writer"

echo "  Granting roles/run.admin on project (deploy Cloud Run services)..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/run.admin"

# Self-binding: allows the SA to act as itself when deploying Cloud Run
# This is required for Workload Identity Federation impersonation flow:
# GitHub OIDC token -> WIF exchange -> short-lived SA token (requires this role on itself)
echo "  Granting roles/iam.serviceAccountTokenCreator on SA itself (WIF impersonation)..."
gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/iam.serviceAccountTokenCreator" \
  --project="$PROJECT_ID"

# Cloud Run deploy requires the deploying SA to be able to act as (impersonate) the
# default Compute Engine service account that Cloud Run uses at runtime.
# Without this binding, `gcloud run deploy` of a NEW service fails with:
#   "Permission 'iam.serviceaccounts.actAs' denied on service account
#    {project-number}-compute@developer.gserviceaccount.com"
COMPUTE_SA="${GCP_PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
echo "  Granting roles/iam.serviceAccountUser on Compute SA (Cloud Run deploy permission)..."
gcloud iam service-accounts add-iam-policy-binding "$COMPUTE_SA" \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/iam.serviceAccountUser" \
  --project="$PROJECT_ID"

# --- Workload Identity Pool ---

echo ""
echo "=== Workload Identity Pool ==="
# A Workload Identity Pool is the GCP container that holds external identity providers.
# Think of it as: "GCP, trust tokens coming from this external system".
# We create one pool per project, scoped to GitHub Actions.
POOL_NAME="github-actions-pool"

if gcloud iam workload-identity-pools describe "$POOL_NAME" \
    --location=global \
    --project="$PROJECT_ID" &>/dev/null; then
  echo "  Workload Identity Pool already exists: $POOL_NAME — skipping"
else
  echo "  Creating Workload Identity Pool: $POOL_NAME"
  gcloud iam workload-identity-pools create "$POOL_NAME" \
    --location=global \
    --display-name="GitHub Actions Pool" \
    --description="Allows GitHub Actions OIDC tokens to authenticate to GCP" \
    --project="$PROJECT_ID"
fi

# --- Workload Identity Provider ---

echo ""
echo "=== Workload Identity Provider ==="
# The Provider tells GCP which OIDC issuer to trust and how to map token claims to GCP attributes.
# GitHub's OIDC issuer is: https://token.actions.githubusercontent.com
# Attribute mapping:
#   google.subject     <- assertion.sub         (unique token identifier)
#   attribute.repository <- assertion.repository  (e.g. "org/repo" — used for the IAM binding below)
#   attribute.actor    <- assertion.actor        (triggering GitHub user, useful for audit)
#   attribute.ref      <- assertion.ref          (branch/tag ref, e.g. "refs/heads/main")
# Attribute condition restricts this provider to tokens from YOUR specific repo only.
PROVIDER_NAME="github-provider"

if gcloud iam workload-identity-pools providers describe "$PROVIDER_NAME" \
    --workload-identity-pool="$POOL_NAME" \
    --location=global \
    --project="$PROJECT_ID" &>/dev/null; then
  echo "  Workload Identity Provider already exists: $PROVIDER_NAME — skipping"
else
  echo "  Creating Workload Identity Provider: $PROVIDER_NAME"
  gcloud iam workload-identity-pools providers create-oidc "$PROVIDER_NAME" \
    --workload-identity-pool="$POOL_NAME" \
    --location=global \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.actor=assertion.actor,attribute.ref=assertion.ref" \
    --attribute-condition="assertion.repository=='${GITHUB_REPO}'" \
    --display-name="GitHub OIDC Provider" \
    --project="$PROJECT_ID"
fi

# --- Workload Identity Binding ---

echo ""
echo "=== Workload Identity Binding ==="
# This binding is the final piece: it authorises tokens from the specific GitHub repo
# to impersonate the CI/CD service account.
#
# principalSet (not principal) is used here — it matches ALL tokens from the repo,
# regardless of which branch or actor triggered the workflow. If you want to restrict
# to main branch only, change to:
#   attribute.ref/refs/heads/main
#
# IAM bindings are idempotent — safe to re-run if already exists.
echo "  Binding GitHub repo OIDC principal to service account: $SA_EMAIL"
gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
  --project="$PROJECT_ID" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${GCP_PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_NAME}/attribute.repository/${GITHUB_REPO}"

echo ""
echo "=== Setup Complete ==="

echo ""
echo "==================================================================="
echo "CI/CD setup complete."
echo ""
echo "Add these as GitHub repository secrets:"
echo "(Settings → Secrets and variables → Actions → New repository secret)"
echo ""
echo "  WIF_PROVIDER"
echo "  projects/${GCP_PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_NAME}/providers/${PROVIDER_NAME}"
echo ""
echo "  WIF_SERVICE_ACCOUNT"
echo "  ${SA_EMAIL}"
echo ""
echo "  GCP_PROJECT_ID"
echo "  ${PROJECT_ID}"
echo ""
echo "Image path for workflows:"
echo "  us-central1-docker.pkg.dev/${PROJECT_ID}/${REGISTRY_REPO}/app"
echo "==================================================================="
