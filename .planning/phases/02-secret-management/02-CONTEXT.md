# Phase 2: Secret Management - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Move all API credentials from config.yaml to GCP Secret Manager. Application reads secrets from environment variables at runtime, with config.yaml fallback for local development. No new capabilities — just changing where secrets are stored and how they're accessed.

</domain>

<decisions>
## Implementation Decisions

### Environment Variable Naming
- NETWORK_FIELD format: INMOBI_SECRET_KEY, APPLOVIN_API_KEY, ADMOB_CLIENT_ID
- No project prefix — simple, readable, Cloud Run standard
- Each credential field is a separate env var (not JSON bundles)
- All secrets and service credentials (Slack webhook, GCS bucket, etc.) moved to env vars

### Secret Manager Naming
- Claude's discretion — choose appropriate GCP Secret Manager naming convention

### Fallback Behavior
- Env var takes priority over config.yaml (12-factor app approach)
- Field-level override: each field independently checks env var first, then config.yaml
- Missing credentials: skip that network, log warning, continue with others (graceful degradation)
- Config class interface stays the same — config.get() internally checks env var first, then YAML

### AdMob OAuth Handling
- OAuth refresh token stored as JSON string in single Secret Manager secret
- Token renewal writes to in-memory cache only (Cloud Run creates fresh instance each run)
- Local dev continues using credentials/admob_token.json file path
- Cloud: env var → parse JSON → use tokens. Local: file path → read JSON → use tokens

### Secret Injection Method
- Cloud Run native secret env vars (gcloud run deploy --set-secrets)
- No Secret Manager API calls in application code — Cloud Run handles injection
- Setup script (scripts/setup-secrets.sh) with gcloud secrets create commands for reproducible setup

### Out of Scope
- Secret rotation — deferred to future work
- Encryption of local credential files
- Secret Manager API client library

### Claude's Discretion
- Exact env var to config.yaml key mapping implementation
- Error messages and logging format for missing credentials
- Setup script structure and documentation

</decisions>

<specifics>
## Specific Ideas

- Config.get() should transparently check env vars — fetchers should not need code changes
- Cloud Run's --set-secrets flag maps Secret Manager secrets to env vars automatically
- 12 network fetchers each have different credential shapes — mapping needs to be comprehensive

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/config.py` Config class: Central config access with nested key support (config.get('networks.inmobi.secret_key')). This is the primary modification target — add env var lookup before YAML lookup.
- `src/utils/token_cache.py` TokenCache: File-based TTL token caching. Works for local dev, in-memory alternative needed for cloud.
- `src/fetchers/admob_fetcher.py`: Uses credentials/admob_token.json for OAuth. Special handling needed for cloud.

### Established Patterns
- All fetchers get credentials via Config class — single integration point
- Config uses dot-notation key access (e.g., 'networks.inmobi.secret_key')
- Fetcher factory creates fetchers based on config presence (graceful skip if no config)

### Integration Points
- `src/config.py` Config.get() — primary change point for env var fallback
- `src/fetchers/admob_fetcher.py` — OAuth token path needs cloud/local branching
- `docker-compose.yml` — needs .env file support for local testing with env vars
- `Dockerfile` — no changes needed (Cloud Run injects env vars at runtime)

</code_context>

<deferred>
## Deferred Ideas

- Secret rotation and versioning — future operational concern
- Encryption of local credential files — nice-to-have, not blocking
- Centralized credential validation at startup — could be a quality improvement

</deferred>

---

*Phase: 02-secret-management*
*Context gathered: 2026-03-02*
