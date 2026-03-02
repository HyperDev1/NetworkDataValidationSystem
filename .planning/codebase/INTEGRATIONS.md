# External Integrations

**Analysis Date:** 2026-03-02

## APIs & External Services

**AppLovin:**
- AppLovin MAX API - Central source for monetization data across ad networks
  - SDK/Client: `aiohttp` with custom fetch logic in `src/fetchers/applovin_fetcher.py`
  - Auth: API key via `applovin.api_key` in config
  - Endpoint: `https://r.applovin.com/maxReport`
  - Data: Network breakdown by platform (Android/iOS) and ad type (Banner/Interstitial/Rewarded)

**Ad Networks (via their APIs):**
- **Mintegral** - `src/fetchers/mintegral_fetcher.py`
  - Auth: Signature-based (skey + secret) via config
  - Data: Revenue, impressions, eCPM by application and ad type

- **Unity Ads** - `src/fetchers/unity_fetcher.py`
  - Auth: API key via `unity_ads.api_key`
  - API: Unity Monetization Stats API
  - Supports filtering by organization and game IDs

- **Google AdMob** - `src/fetchers/admob_fetcher.py`
  - SDK/Client: `google-api-python-client` with OAuth 2.0
  - Auth: OAuth 2.0 (Production mode with token caching)
  - Scopes: `https://www.googleapis.com/auth/admob.readonly`
  - Token storage: `credentials/admob_token.json` (auto-refreshed)
  - API: AdMob API v1 REST
  - Data: Ad performance metrics by app, ad unit, and format

- **Meta Audience Network** - `src/fetchers/meta_fetcher.py`
  - SDK/Client: `aiohttp` with custom implementation
  - Auth: System User Access Token (from Meta Business Manager) via `meta.access_token`
  - API: Meta Graph API v24.0
  - Data: Monetization reports with hourly breakdown

- **IronSource** - `src/fetchers/ironsource_fetcher.py`
  - Auth: Secret key and refresh token based auth
  - Data: Publisher monetization data

- **Liftoff (Vungle)** - `src/fetchers/liftoff_fetcher.py`
  - Auth: API key via `liftoff.api_key`
  - API: Liftoff Publisher Reporting API 2.0
  - Data: Application-level reporting

- **DT Exchange (Digital Turbine/Fyber)** - `src/fetchers/dt_exchange_fetcher.py`
  - Auth: OAuth 2.0 (client_id + client_secret)
  - API: DT Exchange Reporting API
  - Data: Mediation source reports

- **Pangle (ByteDance)** - `src/fetchers/pangle_fetcher.py`
  - Auth: Signature-based (user_id, role_id, secure_key from dashboard)
  - API: Pangle Reporting API v2
  - Data: App performance with timezone/currency support

- **BidMachine SSP** - `src/fetchers/bidmachine_fetcher.py`
  - Auth: Username/password credentials
  - API: BidMachine Reporting API
  - Data: SSP performance metrics

- **InMobi** - `src/fetchers/inmobi_fetcher.py`
  - Auth: API credentials

- **Moloco** - `src/fetchers/moloco_fetcher.py`
  - Auth: Email/password (publisher login) via `moloco.email` + `moloco.password`
  - API: Moloco Publisher Summary API
  - Data: Publisher monetization with platform ID and app bundle filtering

## Data Storage

**Databases:**
- Not used - Stateless fetch and export model

**File Storage:**
- **Google Cloud Storage (GCS)** - Primary export target
  - Connection: GCP service account via `gcp.project_id` and `gcp.bucket_name`
  - Client: `google-cloud-storage` package
  - Format: Parquet files with schema defined in `src/exporters/gcs_exporter.py`
  - Path structure: `gs://{bucket}/network_data/dt={YYYY-MM-DD}/{network}_{platform}_{timestamp}.parquet`
  - Supports Hive partitioning by date for BigQuery external tables
  - Merge mode: Partial updates preserve other networks' data per date

- **Local filesystem** (optional)
  - Dry-run export mode to local directories in `output/` subdirectories
  - Used for testing and development

**Caching:**
- **Token cache** - `src/utils/token_cache.py` stores OAuth tokens for Google services
  - AdMob token: `credentials/admob_token.json`
  - Prevents repeated OAuth flows for production deployments

## Authentication & Identity

**Auth Providers:**
- **Google OAuth 2.0** - Browser-based for AdMob
  - Implementation: `src/fetchers/admob_fetcher.py` with `google-auth-oauthlib`
  - Token refresh: Automatic when expired

- **API Keys** - Multiple networks use static API keys
  - AppLovin, Mintegral, Unity, Liftoff, etc.
  - Stored in `config.yaml` under network-specific sections

- **Signature-based Auth** - Requires key + secret pairs
  - Pangle, Mintegral use HMAC signatures
  - Implemented per-fetcher with request signing logic

- **Custom Auth** - Network-specific implementations
  - DT Exchange: OAuth 2.0 client credentials
  - BidMachine: Username/password
  - Moloco: Email/password login

## Monitoring & Observability

**Error Tracking:**
- Not detected - No external error tracking service (Sentry, etc.) configured

**Logs:**
- **Python logging module** - Core logging framework
  - Level: INFO by default in `main.py` and `service.py`
  - Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
  - Loggers per module: `logging.getLogger(__name__)`
  - Retry logging: Tenacity integrates with logging via `before_sleep_log` callback
  - Output: Stdout/stderr, rotated via external tools (systemd, cron, etc.)

## CI/CD & Deployment

**Hosting:**
- Local/self-hosted - System service via `service.py` for scheduled execution
- Can be deployed to:
  - Cloud Run (GCP) - Serverless Python execution
  - Compute Engine (GCP) - VM-based scheduled tasks
  - Kubernetes - Containerized deployment
  - Traditional servers - Systemd service + cron scheduler

**CI Pipeline:**
- Not detected - No GitHub Actions, GitLab CI, or Jenkins configuration found

**Scheduling:**
- `schedule` library in `service.py` for interval-based execution
- Cron-compatible time scheduling via `get_scheduled_times()` method in `src/config.py`
- Service mode (`--schedule` flag) runs continuous loop with interval checks

## Environment Configuration

**Required env vars:**
- Secrets are managed via `config.yaml` (YAML file, not environment variables)
- Note: `.env` files are not used in this project

**Secrets location:**
- `config.yaml` - Contains all API keys, tokens, and credentials
- GCP service account JSON - Path specified in `gcp.service_account_path`
- AdMob OAuth token - Cached in `credentials/admob_token.json` after first authorization
- GCS authentication: Uses Application Default Credentials (ADC) or explicit service account

## Webhooks & Callbacks

**Incoming:**
- Not used - System is pull-based from network APIs

**Outgoing:**
- **Slack Webhooks** - Outbound notifications
  - Webhook URL: `slack.webhook_url` from config
  - Implementation: `src/notifiers/slack_notifier.py` using `requests`
  - Payload: JSON formatted comparison results with emoji icons per network
  - Trigger: Revenue delta threshold exceeded (configurable via `slack.revenue_delta_threshold`)

---

*Integration audit: 2026-03-02*
