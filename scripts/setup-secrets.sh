#!/usr/bin/env bash
# setup-secrets.sh — Create GCP Secret Manager secrets for Network Data Validation System
#
# Usage:
#   1. Set PROJECT_ID: export PROJECT_ID=your-gcp-project-id
#   2. Set each secret value as an env var (e.g. export APPLOVIN_API_KEY=xxx)
#   3. Run: bash scripts/setup-secrets.sh
#
# For AdMob token: generate locally first (run the app locally with AdMob enabled),
#   then export: ADMOB_TOKEN_JSON=$(cat credentials/admob_token.json)
#
# Secret Manager naming: matches env var names exactly (Cloud Run --set-secrets maps them directly)

set -euo pipefail

# --- Prerequisites ---

if [ -z "${PROJECT_ID:-}" ]; then
  echo "ERROR: PROJECT_ID env var is required. Export it first:"
  echo "  export PROJECT_ID=your-gcp-project-id"
  exit 1
fi

if ! command -v gcloud &>/dev/null; then
  echo "ERROR: gcloud CLI not found. Install Google Cloud SDK."
  exit 1
fi

echo "Setting up secrets for project: $PROJECT_ID"
gcloud config set project "$PROJECT_ID"

# --- Helper ---

create_or_update_secret() {
  local secret_name="$1"
  local secret_value="$2"

  if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" &>/dev/null; then
    echo "  Updating existing secret: $secret_name"
    echo -n "$secret_value" | gcloud secrets versions add "$secret_name" --data-file=- --project="$PROJECT_ID"
  else
    echo "  Creating new secret: $secret_name"
    echo -n "$secret_value" | gcloud secrets create "$secret_name" --data-file=- --replication-policy=automatic --project="$PROJECT_ID"
  fi
}

# --- Secret creation ---

echo ""
echo "=== AppLovin ==="
[ -n "${APPLOVIN_API_KEY:-}" ] && create_or_update_secret "APPLOVIN_API_KEY" "$APPLOVIN_API_KEY" || echo "  SKIP: APPLOVIN_API_KEY not set"
[ -n "${APPLOVIN_PACKAGE_NAME:-}" ] && create_or_update_secret "APPLOVIN_PACKAGE_NAME" "$APPLOVIN_PACKAGE_NAME" || echo "  SKIP: APPLOVIN_PACKAGE_NAME not set"

echo ""
echo "=== Mintegral ==="
[ -n "${MINTEGRAL_SKEY:-}" ] && create_or_update_secret "MINTEGRAL_SKEY" "$MINTEGRAL_SKEY" || echo "  SKIP: MINTEGRAL_SKEY not set"
[ -n "${MINTEGRAL_SECRET:-}" ] && create_or_update_secret "MINTEGRAL_SECRET" "$MINTEGRAL_SECRET" || echo "  SKIP: MINTEGRAL_SECRET not set"

echo ""
echo "=== Unity Ads ==="
[ -n "${UNITY_ADS_API_KEY:-}" ] && create_or_update_secret "UNITY_ADS_API_KEY" "$UNITY_ADS_API_KEY" || echo "  SKIP: UNITY_ADS_API_KEY not set"
[ -n "${UNITY_ADS_ORGANIZATION_ID:-}" ] && create_or_update_secret "UNITY_ADS_ORGANIZATION_ID" "$UNITY_ADS_ORGANIZATION_ID" || echo "  SKIP: UNITY_ADS_ORGANIZATION_ID not set"

echo ""
echo "=== AdMob ==="
[ -n "${ADMOB_PUBLISHER_ID:-}" ] && create_or_update_secret "ADMOB_PUBLISHER_ID" "$ADMOB_PUBLISHER_ID" || echo "  SKIP: ADMOB_PUBLISHER_ID not set"
[ -n "${ADMOB_TOKEN_JSON:-}" ] && create_or_update_secret "ADMOB_TOKEN_JSON" "$ADMOB_TOKEN_JSON" || echo "  SKIP: ADMOB_TOKEN_JSON not set (generate locally first: cat credentials/admob_token.json)"
[ -n "${ADMOB_OAUTH_CREDENTIALS_PATH:-cloud-run}" ] && create_or_update_secret "ADMOB_OAUTH_CREDENTIALS_PATH" "${ADMOB_OAUTH_CREDENTIALS_PATH:-cloud-run}" || echo "  SKIP: ADMOB_OAUTH_CREDENTIALS_PATH not set"

echo ""
echo "=== Meta ==="
[ -n "${META_ACCESS_TOKEN:-}" ] && create_or_update_secret "META_ACCESS_TOKEN" "$META_ACCESS_TOKEN" || echo "  SKIP: META_ACCESS_TOKEN not set"
[ -n "${META_BUSINESS_ID:-}" ] && create_or_update_secret "META_BUSINESS_ID" "$META_BUSINESS_ID" || echo "  SKIP: META_BUSINESS_ID not set"

echo ""
echo "=== Moloco ==="
[ -n "${MOLOCO_EMAIL:-}" ] && create_or_update_secret "MOLOCO_EMAIL" "$MOLOCO_EMAIL" || echo "  SKIP: MOLOCO_EMAIL not set"
[ -n "${MOLOCO_PASSWORD:-}" ] && create_or_update_secret "MOLOCO_PASSWORD" "$MOLOCO_PASSWORD" || echo "  SKIP: MOLOCO_PASSWORD not set"
[ -n "${MOLOCO_PLATFORM_ID:-}" ] && create_or_update_secret "MOLOCO_PLATFORM_ID" "$MOLOCO_PLATFORM_ID" || echo "  SKIP: MOLOCO_PLATFORM_ID not set"

echo ""
echo "=== BidMachine ==="
[ -n "${BIDMACHINE_USERNAME:-}" ] && create_or_update_secret "BIDMACHINE_USERNAME" "$BIDMACHINE_USERNAME" || echo "  SKIP: BIDMACHINE_USERNAME not set"
[ -n "${BIDMACHINE_PASSWORD:-}" ] && create_or_update_secret "BIDMACHINE_PASSWORD" "$BIDMACHINE_PASSWORD" || echo "  SKIP: BIDMACHINE_PASSWORD not set"

echo ""
echo "=== Liftoff ==="
[ -n "${LIFTOFF_API_KEY:-}" ] && create_or_update_secret "LIFTOFF_API_KEY" "$LIFTOFF_API_KEY" || echo "  SKIP: LIFTOFF_API_KEY not set"

echo ""
echo "=== DT Exchange ==="
[ -n "${DT_EXCHANGE_CLIENT_ID:-}" ] && create_or_update_secret "DT_EXCHANGE_CLIENT_ID" "$DT_EXCHANGE_CLIENT_ID" || echo "  SKIP: DT_EXCHANGE_CLIENT_ID not set"
[ -n "${DT_EXCHANGE_CLIENT_SECRET:-}" ] && create_or_update_secret "DT_EXCHANGE_CLIENT_SECRET" "$DT_EXCHANGE_CLIENT_SECRET" || echo "  SKIP: DT_EXCHANGE_CLIENT_SECRET not set"

echo ""
echo "=== Pangle ==="
[ -n "${PANGLE_USER_ID:-}" ] && create_or_update_secret "PANGLE_USER_ID" "$PANGLE_USER_ID" || echo "  SKIP: PANGLE_USER_ID not set"
[ -n "${PANGLE_ROLE_ID:-}" ] && create_or_update_secret "PANGLE_ROLE_ID" "$PANGLE_ROLE_ID" || echo "  SKIP: PANGLE_ROLE_ID not set"
[ -n "${PANGLE_SECURE_KEY:-}" ] && create_or_update_secret "PANGLE_SECURE_KEY" "$PANGLE_SECURE_KEY" || echo "  SKIP: PANGLE_SECURE_KEY not set"

echo ""
echo "=== IronSource ==="
[ -n "${IRONSOURCE_USERNAME:-}" ] && create_or_update_secret "IRONSOURCE_USERNAME" "$IRONSOURCE_USERNAME" || echo "  SKIP: IRONSOURCE_USERNAME not set"
[ -n "${IRONSOURCE_SECRET_KEY:-}" ] && create_or_update_secret "IRONSOURCE_SECRET_KEY" "$IRONSOURCE_SECRET_KEY" || echo "  SKIP: IRONSOURCE_SECRET_KEY not set"

echo ""
echo "=== InMobi ==="
[ -n "${INMOBI_ACCOUNT_ID:-}" ] && create_or_update_secret "INMOBI_ACCOUNT_ID" "$INMOBI_ACCOUNT_ID" || echo "  SKIP: INMOBI_ACCOUNT_ID not set"
[ -n "${INMOBI_SECRET_KEY:-}" ] && create_or_update_secret "INMOBI_SECRET_KEY" "$INMOBI_SECRET_KEY" || echo "  SKIP: INMOBI_SECRET_KEY not set"
[ -n "${INMOBI_USERNAME:-}" ] && create_or_update_secret "INMOBI_USERNAME" "$INMOBI_USERNAME" || echo "  SKIP: INMOBI_USERNAME not set"

echo ""
echo "=== Slack ==="
[ -n "${SLACK_WEBHOOK_URL:-}" ] && create_or_update_secret "SLACK_WEBHOOK_URL" "$SLACK_WEBHOOK_URL" || echo "  SKIP: SLACK_WEBHOOK_URL not set"

echo ""
echo "=== GCP ==="
[ -n "${GCP_BUCKET_NAME:-}" ] && create_or_update_secret "GCP_BUCKET_NAME" "$GCP_BUCKET_NAME" || echo "  SKIP: GCP_BUCKET_NAME not set"
[ -n "${GCP_PROJECT_ID:-}" ] && create_or_update_secret "GCP_PROJECT_ID" "$GCP_PROJECT_ID" || echo "  SKIP: GCP_PROJECT_ID not set"

# --- Cloud Run deploy snippet ---

echo ""
echo "==================================================================="
echo "Secret Manager setup complete."
echo ""
echo "Cloud Run deploy command (copy and customize):"
echo ""
echo "gcloud run jobs deploy network-data-validation \\"
echo "  --image gcr.io/\$PROJECT_ID/network-data-validation:latest \\"
echo "  --region us-central1 \\"
echo "  --set-secrets=APPLOVIN_API_KEY=APPLOVIN_API_KEY:latest,\\"
echo "APPLOVIN_PACKAGE_NAME=APPLOVIN_PACKAGE_NAME:latest,\\"
echo "MINTEGRAL_SKEY=MINTEGRAL_SKEY:latest,\\"
echo "MINTEGRAL_SECRET=MINTEGRAL_SECRET:latest,\\"
echo "UNITY_ADS_API_KEY=UNITY_ADS_API_KEY:latest,\\"
echo "UNITY_ADS_ORGANIZATION_ID=UNITY_ADS_ORGANIZATION_ID:latest,\\"
echo "ADMOB_PUBLISHER_ID=ADMOB_PUBLISHER_ID:latest,\\"
echo "ADMOB_TOKEN_JSON=ADMOB_TOKEN_JSON:latest,\\"
echo "ADMOB_OAUTH_CREDENTIALS_PATH=ADMOB_OAUTH_CREDENTIALS_PATH:latest,\\"
echo "META_ACCESS_TOKEN=META_ACCESS_TOKEN:latest,\\"
echo "META_BUSINESS_ID=META_BUSINESS_ID:latest,\\"
echo "MOLOCO_EMAIL=MOLOCO_EMAIL:latest,\\"
echo "MOLOCO_PASSWORD=MOLOCO_PASSWORD:latest,\\"
echo "MOLOCO_PLATFORM_ID=MOLOCO_PLATFORM_ID:latest,\\"
echo "BIDMACHINE_USERNAME=BIDMACHINE_USERNAME:latest,\\"
echo "BIDMACHINE_PASSWORD=BIDMACHINE_PASSWORD:latest,\\"
echo "LIFTOFF_API_KEY=LIFTOFF_API_KEY:latest,\\"
echo "DT_EXCHANGE_CLIENT_ID=DT_EXCHANGE_CLIENT_ID:latest,\\"
echo "DT_EXCHANGE_CLIENT_SECRET=DT_EXCHANGE_CLIENT_SECRET:latest,\\"
echo "PANGLE_USER_ID=PANGLE_USER_ID:latest,\\"
echo "PANGLE_ROLE_ID=PANGLE_ROLE_ID:latest,\\"
echo "PANGLE_SECURE_KEY=PANGLE_SECURE_KEY:latest,\\"
echo "IRONSOURCE_USERNAME=IRONSOURCE_USERNAME:latest,\\"
echo "IRONSOURCE_SECRET_KEY=IRONSOURCE_SECRET_KEY:latest,\\"
echo "INMOBI_ACCOUNT_ID=INMOBI_ACCOUNT_ID:latest,\\"
echo "INMOBI_SECRET_KEY=INMOBI_SECRET_KEY:latest,\\"
echo "INMOBI_USERNAME=INMOBI_USERNAME:latest,\\"
echo "SLACK_WEBHOOK_URL=SLACK_WEBHOOK_URL:latest,\\"
echo "GCP_BUCKET_NAME=GCP_BUCKET_NAME:latest,\\"
echo "GCP_PROJECT_ID=GCP_PROJECT_ID:latest"
echo "==================================================================="
