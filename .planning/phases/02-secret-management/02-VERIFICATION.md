---
phase: 02-secret-management
verified: 2026-03-02T11:30:00Z
status: human_needed
score: 15/15 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 13/15
  gaps_closed:
    - "setup-secrets.sh documents the --set-secrets flag string for gcloud run deploy (line 140: ADMOB_OAUTH_CREDENTIALS_PATH=ADMOB_OAUTH_CREDENTIALS_PATH:latest present)"
    - "AdmobFetcher token refresh writes to in-memory cache only in Cloud Run — factory gate now passable because ADMOB_OAUTH_CREDENTIALS_PATH secret created with cloud-run placeholder (line 68 of setup-secrets.sh)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "End-to-end Cloud Run AdMob activation"
    expected: "When ADMOB_TOKEN_JSON, ADMOB_PUBLISHER_ID, and ADMOB_OAUTH_CREDENTIALS_PATH are all set as env vars (ADMOB_OAUTH_CREDENTIALS_PATH='cloud-run'), AdmobFetcher is created by factory.py and successfully authenticates using the JSON token. _save_token logs 'Cloud Run mode: skipping token file write'. No file I/O attempted against the placeholder path."
    why_human: "Requires live GCP credentials and a Cloud Run deployment to verify the full auth path. Cannot simulate google.oauth2.credentials.Credentials.from_authorized_user_info locally without real OAuth tokens."
---

# Phase 2: Secret Management Verification Report

**Phase Goal:** All API credentials live in GCP Secret Manager and the application reads them without touching config.yaml at runtime
**Verified:** 2026-03-02T11:30:00Z
**Status:** human_needed (all automated checks pass; 1 human test remains from initial verification)
**Re-verification:** Yes — after gap closure via plan 02-03

## Re-Verification Summary

Previous status: `gaps_found` (13/15, 2 partial truths)
Current status: `human_needed` (15/15 automated checks pass)

Both gaps from the initial verification were closed by plan 02-03 (commit `032a1a2`):

1. **Gap 1 (Truth #12):** ADMOB_OAUTH_CREDENTIALS_PATH=ADMOB_OAUTH_CREDENTIALS_PATH:latest added to the --set-secrets deploy snippet at line 140 of `scripts/setup-secrets.sh`. CLOSED.
2. **Gap 2 (Truth #15):** ADMOB_OAUTH_CREDENTIALS_PATH added to the secret creation block at line 68 with `${ADMOB_OAUTH_CREDENTIALS_PATH:-cloud-run}` default. When the operator runs setup-secrets.sh without setting this env var, the secret is automatically created with value "cloud-run" — a non-empty placeholder that passes factory.py's `config.get('oauth_credentials_path')` truthy check. `_authenticate_oauth()` checks `ADMOB_TOKEN_JSON` first, so the placeholder value is never opened as a file. CLOSED.

No regressions detected. All 13 previously-passing truths remain intact.

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Config.get() checks environment variable first, then falls back to config.yaml value | VERIFIED | `src/config.py` lines 157-161: `env_key` lookup before dict traversal. |
| 2 | Env var naming follows NETWORK_FIELD pattern (e.g., INMOBI_SECRET_KEY, APPLOVIN_API_KEY) | VERIFIED | `_ENV_VAR_MAP` at lines 15-60 of config.py. All 30 mappings follow the documented convention. |
| 3 | Each credential field is independently overridable by its own env var | VERIFIED | 30 separate entries in `_ENV_VAR_MAP`, one per credential field. |
| 4 | Missing env var with config.yaml fallback available: uses YAML value silently | VERIFIED | `_merge_env_vars` skips when `os.environ.get(env_var) is None`; `get()` falls back to dict traversal. |
| 5 | Missing env var with no config.yaml fallback: returns None (graceful skip) | VERIFIED | `get()` returns `default` (None) when key traversal fails. |
| 6 | docker-compose.yml supports env_file: .env for local testing with env vars | VERIFIED | `docker-compose.yml` line 10: `env_file:` directive present. 30 `# ENV:` annotations in config.yaml.example. |
| 7 | config.yaml.example documents every env var name alongside each credential field | VERIFIED | 30 `# ENV: VARNAME` annotations confirmed. Header block documents naming convention. |
| 8 | _load_config() merges env vars into self.config so get_networks_config() returns env-var-populated data | VERIFIED | `_load_config()` calls `_merge_env_vars()` at line 96. `_merge_env_vars` also auto-sets `enabled: True` for any network receiving an env var. |
| 9 | FetcherFactory.create_all_fetchers() receives env var values via get_networks_config() when config.yaml absent | VERIFIED | `factory.py` line 205: `networks_config = config.get_networks_config()`. Env vars populate this dict via `_merge_env_vars`. |
| 10 | All 12 network fetchers receive credential values from env vars in Cloud Run (config.yaml absent) | VERIFIED | `_merge_env_vars` populates all network sub-dicts. `enabled: True` auto-set for any network with at least one env var injected. |
| 11 | scripts/setup-secrets.sh creates all Secret Manager secrets with gcloud secrets create commands | VERIFIED | `create_or_update_secret()` at line 34 handles both create and update. All 29 secrets covered (28 original + ADMOB_OAUTH_CREDENTIALS_PATH). |
| 12 | setup-secrets.sh documents the --set-secrets flag string for gcloud run deploy | VERIFIED | Line 140: `echo "ADMOB_OAUTH_CREDENTIALS_PATH=ADMOB_OAUTH_CREDENTIALS_PATH:latest,\\"` present. All 29 secrets in the deploy snippet. Bash syntax: OK (`bash -n` passes). |
| 13 | AdmobFetcher reads ADMOB_TOKEN_JSON env var when present and uses it in-memory (no file write) | VERIFIED | `admob_fetcher.py` lines 112-121: env var check first, `Credentials.from_authorized_user_info` used. |
| 14 | AdmobFetcher falls back to token_path file when ADMOB_TOKEN_JSON env var is absent (local dev unchanged) | VERIFIED | `admob_fetcher.py` lines 123-130: file path branch executes when env var not set. |
| 15 | AdmobFetcher token refresh writes to in-memory cache only in Cloud Run (no file write attempt) | VERIFIED | `_save_token()` at lines 183-185: checks `os.environ.get('ADMOB_TOKEN_JSON')` and returns early. Factory gate now passable: `ADMOB_OAUTH_CREDENTIALS_PATH` secret created with "cloud-run" placeholder (line 68), `config.py` maps it to `networks.admob.oauth_credentials_path` via `_merge_env_vars`, factory truthy check passes. Full chain: setup-secrets.sh -> Secret Manager -> Cloud Run env var injection -> config._merge_env_vars -> networks.admob.oauth_credentials_path = "cloud-run" -> factory.create_fetcher truthy check passes -> AdmobFetcher created -> _authenticate_oauth reads ADMOB_TOKEN_JSON -> _save_token skips file write. |

**Score:** 15/15 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/config.py` | Config class with `_merge_env_vars()` and env var override in `get()` | VERIFIED | 30-entry `_ENV_VAR_MAP`, `_merge_env_vars()` (lines 98-140), `_load_config()` (line 76), `get()` (line 142) — all present and wired. |
| `docker-compose.yml` | `env_file` directive with `required: false` | VERIFIED | Line 10: `env_file:` present. |
| `config.yaml.example` | `# ENV: VARNAME` annotations on all credential fields | VERIFIED | 30 annotations confirmed by count. ADMOB_OAUTH_CREDENTIALS_PATH at line 44. |
| `src/fetchers/admob_fetcher.py` | `ADMOB_TOKEN_JSON` env var support in `_authenticate_oauth()` and `_save_token()` | VERIFIED | Lines 112-121: env var branch. Lines 179-185: `_save_token` early-return guard. |
| `scripts/setup-secrets.sh` | Executable bash script creating all Secret Manager secrets with complete deploy snippet | VERIFIED | 29 secrets covered including ADMOB_OAUTH_CREDENTIALS_PATH (line 68 with cloud-run default, line 140 in deploy snippet). `bash -n` syntax check passes. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/config.py` | `config.yaml.example` | `# ENV: VARNAME` annotations match `_ENV_VAR_MAP` keys | VERIFIED | All 30 env var names in `_ENV_VAR_MAP` appear as `# ENV:` annotations including `ADMOB_OAUTH_CREDENTIALS_PATH` at line 44. |
| `docker-compose.yml` | `.env` | `env_file` reference | VERIFIED | `env_file:` present — optional, does not break if absent. |
| `src/config.py _merge_env_vars()` | `src/fetchers/factory.py create_all_fetchers()` | `get_networks_config()` returns env-var-populated dict | VERIFIED | `factory.py` calls `config.get_networks_config()`. `_merge_env_vars` writes to all network sub-dicts. |
| `scripts/setup-secrets.sh` | `config.yaml.example` | Secret names match `# ENV:` annotations | VERIFIED | All 29 secret names in `setup-secrets.sh` match `# ENV:` annotations in `config.yaml.example`. |
| `src/fetchers/admob_fetcher.py` | `src/config.py` | `ADMOB_TOKEN_JSON` env var — same pattern as `Config.get()` | VERIFIED | `os.environ.get('ADMOB_TOKEN_JSON')` at line 112. Consistent with `_ENV_VAR_MAP` pattern. |
| `scripts/setup-secrets.sh ADMOB_OAUTH_CREDENTIALS_PATH` | `src/fetchers/factory.py required_key='oauth_credentials_path'` | Cloud Run env var -> `config._merge_env_vars` -> `networks.admob.oauth_credentials_path` -> factory truthy check | VERIFIED | Line 68 creates secret with "cloud-run" placeholder. `config.py` line 27 maps `ADMOB_OAUTH_CREDENTIALS_PATH` to `['networks', 'admob', 'oauth_credentials_path']`. `factory.py` line 54: `required_key='oauth_credentials_path'`. Chain is complete. |
| `scripts/setup-secrets.sh --set-secrets snippet` | `src/config.py _ENV_VAR_MAP` | `ADMOB_OAUTH_CREDENTIALS_PATH=ADMOB_OAUTH_CREDENTIALS_PATH:latest` maps to correct path | VERIFIED | Line 140 of `setup-secrets.sh` echoes the entry. `config.py` line 27 confirms the mapping. |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SEC-01 | 02-01-PLAN.md, 02-02-PLAN.md, 02-03-PLAN.md | All API keys/tokens/credentials moved to GCP Secret Manager | VERIFIED | `config.yaml` gitignored. `credentials/` excluded from git. `setup-secrets.sh` provides complete GCP Secret Manager setup runbook for all 29 secrets (28 network credentials + ADMOB_OAUTH_CREDENTIALS_PATH factory gate). No live secrets in source control. |
| SEC-02 | 02-02-PLAN.md, 02-03-PLAN.md | Cloud Run injects secrets as environment variables | VERIFIED | `setup-secrets.sh` prints complete `gcloud run jobs deploy --set-secrets` command covering all 29 secrets including ADMOB_OAUTH_CREDENTIALS_PATH. `config._merge_env_vars` reads them at runtime. No Secret Manager API calls in application code. |
| SEC-03 | 02-01-PLAN.md | `config.py` checks env vars first, falls back to config.yaml | VERIFIED | `Config.get()` lines 157-161 checks env var before YAML traversal. `_merge_env_vars()` populates `self.config` at construction. Both layers confirmed. |
| SEC-04 | 02-02-PLAN.md, 02-03-PLAN.md | AdMob OAuth refresh token stored in Secret Manager, read by container at runtime | VERIFIED | `ADMOB_TOKEN_JSON` secret documented in `setup-secrets.sh`. `admob_fetcher._authenticate_oauth()` reads it first. `_save_token()` skips file write when env var is set. Factory gate now satisfied: `ADMOB_OAUTH_CREDENTIALS_PATH` secret is created with "cloud-run" placeholder, injected into Cloud Run, and maps to `networks.admob.oauth_credentials_path` via `config._merge_env_vars`. AdmobFetcher is created and uses `ADMOB_TOKEN_JSON` for authentication. |

**All 4 requirement IDs (SEC-01, SEC-02, SEC-03, SEC-04) from PLAN frontmatter accounted for. No orphaned requirements.**

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/fetchers/admob_fetcher.py` | 1 | UTF-8 BOM character (U+FEFF) at file start | Info | No runtime impact — CPython handles UTF-8 BOM correctly as an encoding declaration. Low risk; worth cleaning in a future pass. |
| `src/fetchers/admob_fetcher.py` | 25 | `Credentials = None  # Type hint placeholder` | Info | Deliberate import-fallback pattern for missing `google-auth` library. Not a stub. |

No blocker anti-patterns. No TODO/FIXME comments. No empty return stubs. No regressions introduced by plan 02-03 (diff was additive-only: two lines added to `setup-secrets.sh`).

---

### Human Verification Required

#### 1. AdMob Cloud Run End-to-End Auth

**Test:** In a Cloud Run environment (or locally with env vars simulating Cloud Run), set:
- `ADMOB_TOKEN_JSON=<real OAuth token JSON from credentials/admob_token.json>`
- `ADMOB_PUBLISHER_ID=<real publisher id>`
- `ADMOB_OAUTH_CREDENTIALS_PATH=cloud-run` (the placeholder value that setup-secrets.sh creates)

Start the container and confirm:
1. `factory.py` creates AdmobFetcher (does not skip with "admob missing required key: oauth_credentials_path")
2. `_authenticate_oauth` logs "Loaded AdMob OAuth token from ADMOB_TOKEN_JSON env var"
3. `_save_token` logs "Cloud Run mode: skipping token file write (in-memory only)"
4. No file I/O attempted against the string "cloud-run"

**Expected:** AdMob fetcher initializes successfully and returns data without any file system access.

**Why human:** Requires live GCP credentials and either a real Cloud Run deployment or real OAuth tokens. Cannot verify `Credentials.from_authorized_user_info` flow without a real Google OAuth token that has not expired.

---

### Gaps Summary

No gaps. Both gaps from the initial verification are closed.

The gap root cause was: `ADMOB_OAUTH_CREDENTIALS_PATH` was absent from `scripts/setup-secrets.sh`, so operators following the script exactly would have `ADMOB_TOKEN_JSON` injected into Cloud Run but `factory.py`'s `required_key='oauth_credentials_path'` gate would silently skip AdMob.

The fix (plan 02-03, commit `032a1a2`) added two lines to `setup-secrets.sh`:
- Line 68: secret creation with `${ADMOB_OAUTH_CREDENTIALS_PATH:-cloud-run}` default — always creates the secret, even when the operator does not set the env var
- Line 140: `ADMOB_OAUTH_CREDENTIALS_PATH=ADMOB_OAUTH_CREDENTIALS_PATH:latest` in the deploy snippet

The wiring chain is now complete: `setup-secrets.sh` creates secret -> Cloud Run injects as `ADMOB_OAUTH_CREDENTIALS_PATH` env var -> `config._merge_env_vars` writes "cloud-run" to `networks.admob.oauth_credentials_path` -> `factory.create_fetcher` truthy check passes -> `AdmobFetcher` created -> `_authenticate_oauth` reads `ADMOB_TOKEN_JSON` (ignoring the placeholder path) -> `_save_token` skips file write.

One human verification item remains (carried forward from initial verification): the full Cloud Run auth flow with real GCP credentials.

---

_Verified: 2026-03-02T11:30:00Z_
_Verifier: Claude (gsd-verifier)_
