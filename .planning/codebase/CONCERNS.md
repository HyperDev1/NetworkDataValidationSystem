# Codebase Concerns

**Analysis Date:** 2026-03-02

## Tech Debt

**Monolithic main.py file:**
- Issue: `main.py` is 905 lines with multiple responsibilities (validation logic, data transformation, scheduling, CLI handling) all mixed together
- Files: `main.py`
- Impact: Hard to test individual functions, difficult to reuse logic, high coupling between concerns
- Fix approach: Extract functions into modules:
  - `src/comparison.py` - For `_create_comparison_rows`, `_create_all_comparison_rows`, `_calculate_delta` functions
  - `src/scheduling.py` - For `run_scheduled` function
  - Move `run_validation` into a service class or to `validation_service.py`

**Duplicate network display name mapping:**
- Issue: `NETWORK_DISPLAY_NAME_MAP` exists in both `main.py` (lines 47-77) and `validation_service.py` (lines 38-76)
- Files: `main.py`, `src/validation_service.py`
- Impact: Changes to network naming require updating two places; inconsistency risk
- Fix approach: Move to single shared location like `src/constants.py` or `src/enums.py`, import everywhere

**Nested function definitions:**
- Issue: `parse_delta` is defined inside `run_validation` (line 562-575) where it's used once
- Files: `main.py`
- Impact: Unnecessary nesting, harder to test/reuse the parsing logic
- Fix approach: Move to module-level function or utility module like `src/utils/delta.py`

**Mixed async/sync patterns:**
- Issue: `run_validation` is async, but `run_single_validation` is sync wrapper calling `asyncio.run()` (line 793)
- Files: `main.py` (lines 768-801)
- Impact: Inconsistent error handling between async and sync paths
- Fix approach: Standardize on async throughout or create separate sync/async entry points

**Broad exception handling:**
- Issue: Multiple `except Exception as e:` blocks that catch all exceptions without specific handling
- Files: `main.py` (lines 353-362, 415-424, 468-470, 851-853, 863-866)
- Impact: Masks actual errors, makes debugging difficult, prevents proper error recovery
- Fix approach: Catch specific exception types (KeyError, ValueError, TimeoutError, etc.)

**Loose error handling in fetcher closing:**
- Issue: Multiple `try/except` blocks that silently ignore errors when closing fetchers (lines 358-362, 420-424)
- Files: `main.py`
- Impact: Resource leaks not detected, silent failures
- Fix approach: Log warnings even for secondary failures, use context managers properly

## Known Bugs

**Delta calculation with infinity symbol:**
- Symptoms: When MAX is 0 but network has data, delta is set to "+∞%" (line 96, 644)
- Files: `main.py` (lines 91-100), `src/validation_service.py` (lines 639-648)
- Trigger: Network has impressions but AppLovin MAX reports 0 for a specific app/ad_type
- Workaround: Slack notifier has `parse_delta_percentage` to handle "∞" strings, but this is fragile

**Unsafe dictionary access in comparison creation:**
- Symptoms: `IndexError` or undefined dates when extracting platform/ad_type from row data
- Files: `main.py` (lines 170-171, 238-240)
- Trigger: Malformed row data from AppLovin API
- Workaround: `.get()` with defaults is used for most fields, but `row['ad_type']` is accessed directly

**Missing None checks for network data:**
- Symptoms: `NoneType` errors when accessing `daily_data` if fetch returned None
- Files: `main.py` (lines 179-189, 260-269), `validation_service.py` (lines 579-601)
- Trigger: Network API failure results in None being stored in `network_data[network_key]`
- Workaround: Code checks `if network_key in network_data` but doesn't verify the value isn't None

## Security Considerations

**No input validation on date parameters:**
- Risk: Date strings from CLI args are parsed without validation; malformed dates could cause crashes
- Files: `main.py` (lines 774-783)
- Current mitigation: Try/except on `datetime.strptime` catches parsing errors
- Recommendations: Use a date validation library or strict regex pattern for YYYY-MM-DD format

**Credentials stored in config.yaml file:**
- Risk: API keys, tokens, and credentials in plaintext in config.yaml (required by all fetchers)
- Files: Configuration loaded in `src/config.py` (line 30-31)
- Current mitigation: `.gitignore` excludes config.yaml; user must handle security
- Recommendations:
  - Support environment variables (current: only some networks support this via Config)
  - Use credential managers (AWS Secrets Manager, Google Secret Manager)
  - Document security best practices in README

**Webhooks expose network-level sensitive data:**
- Risk: Slack webhook shows detailed revenue/impression data per network that could reveal business metrics
- Files: `src/notifiers/slack_notifier.py` (lines 140-248)
- Current mitigation: None - all data is sent to Slack
- Recommendations: Add config option to redact specific networks or metrics before sending

**OAuth token storage in fetchers:**
- Risk: AdMob tokens stored in `credentials/admob_token.json` without encryption
- Files: `src/fetchers/admob_fetcher.py` (lines 1-50), token cache: `src/utils/token_cache.py`
- Current mitigation: File permissions (OS-level)
- Recommendations: Encrypt token files or use secure credential storage

## Performance Bottlenecks

**No caching of OAuth tokens across runs:**
- Problem: Each AdMob request re-authenticates if token is close to expiry
- Files: `src/fetchers/admob_fetcher.py`, `src/utils/token_cache.py`
- Cause: Token validation happens on every fetch, no session reuse between CLI runs
- Improvement path: Redis/memcached for shared token cache or longer-lived token storage

**Synchronous HTTP requests in AppLovin fetcher:**
- Problem: `ApplovinFetcher.fetch_data()` is async but internally uses sync `requests` library
- Files: `src/fetchers/admob_fetcher.py` (and likely others)
- Cause: Older fetchers use `requests` instead of `aiohttp`
- Improvement path: Migrate all fetchers to use `aiohttp` for true async I/O

**No connection pooling in some HTTP clients:**
- Problem: Multiple network fetches create new HTTP sessions repeatedly
- Files: Most fetcher implementations create `aiohttp.ClientSession` per-fetch
- Cause: Session management inconsistent across fetchers
- Improvement path: Create persistent shared session in config or dependency injection

**Slack notification blocks built at runtime:**
- Problem: `_build_threshold_exceeded_blocks` and `_build_all_normal_blocks` construct massive JSON payloads for each report
- Files: `src/notifiers/slack_notifier.py` (lines 140-248)
- Cause: No message templates or caching
- Improvement path: Use template system or pre-computed blocks

## Fragile Areas

**Slack notifier formatting logic:**
- Files: `src/notifiers/slack_notifier.py` (1264 lines)
- Why fragile:
  - Deeply nested Slack block construction (multiple levels of dictionaries)
  - String formatting for table output is manual (lines 92-138)
  - Delta percentage parsing has multiple fallbacks: "∞", "N/A", "-∞", "inf", "-inf", ""
  - If Slack API changes block format, entire formatting breaks
- Safe modification: Write unit tests for each block type before refactoring
- Test coverage: None visible - no `test_slack_notifier.py` file
- Recommendation: Extract block builders into separate functions with explicit types (TypedDict)

**Network data daily_data structure:**
- Files: All fetchers populate `daily_data` with `{date: {platform: {ad_type: {impressions, revenue, ecpm}}}}`
- Why fragile:
  - Data structure is inferred from code, not documented
  - Type hints use generic `Dict` instead of TypedDict
  - Different fetchers may have inconsistent structures (see base_fetcher.py line 42-50)
  - Merging logic assumes specific nesting in `validation_service.py` (lines 579-601)
- Safe modification:
  1. Define strict TypedDict for `daily_data` structure
  2. Add validation in base fetcher to enforce structure
  3. Write schema validator
- Test coverage: Gaps in fetcher tests

**Comparison row creation logic:**
- Files: `main.py` (lines 138-220, 223-298), `validation_service.py` (lines 518-637)
- Why fragile:
  - Two nearly identical functions `_create_comparison_rows` and `_create_all_comparison_rows` in main.py
  - Complex nested logic for matching MAX rows to network data
  - Platform detection relies on string matching "iOS" (line 170, 238)
  - Ad type is lowercased but not validated against enum
- Safe modification:
  1. Consolidate into single function with parameters
  2. Add platform enum to replace string matching
  3. Add validation for ad_type
- Test coverage: Gaps in comparison logic tests

**Inmobi session management:**
- Files: `src/fetchers/inmobi_fetcher.py`
- Why fragile:
  - `_session_id` state variable (line 138) persists across fetches
  - If session expires mid-fetch, no recovery mechanism
  - Session creation failure silently returns None
- Safe modification: Wrap session management in context manager
- Test coverage: No visible test for session lifecycle

## Scaling Limits

**No pagination for large data sets:**
- Current capacity: Fetchers assume data fits in single API response
- Limit: Will fail or be truncated if networks have millions of impressions
- Files: Most fetchers lack pagination loops
- Scaling path: Add `limit` and `offset` parameters to API calls, loop until no more data

**Single-threaded Slack message sending:**
- Current capacity: One webhook call per report
- Limit: If Slack API is slow, blocks validation completion
- Files: `src/notifiers/slack_notifier.py` (line 248: `_send_to_slack`)
- Scaling path: Queue Slack messages to background worker or use async requests

**GCS export timing:**
- Current capacity: Exports entire comparison data set to single Parquet file per day/network
- Limit: Files could grow to >500MB for busy networks over time
- Files: `src/exporters/gcs_exporter.py` (lines 460-463 in main.py)
- Scaling path: Implement hourly partitioning, compress Parquet files, use delta format

**In-memory storage of network data:**
- Current capacity: All fetched data held in memory simultaneously (line 385)
- Limit: With 12 networks × 7 days × daily breakdown = ~700-1000 rows per network × data per row
- Files: `main.py` (line 385), `validation_service.py` (line 240-245)
- Scaling path: Stream data to disk/GCS instead of accumulating

## Dependencies at Risk

**Old versions of Google Cloud libraries:**
- Risk: `google-cloud-storage>=2.14.0` and `google-cloud-bigquery>=3.14.0` are pinned but outdated
- Impact: Security patches, bug fixes, feature improvements unavailable
- Migration plan: Update to latest versions (3.x+), test thoroughly
- Files: `Pipfile`, `requirements.txt`

**PyYAML safe_load doesn't validate schema:**
- Risk: Invalid config.yaml loads without errors, fails at runtime
- Impact: Difficult debugging of configuration issues
- Current mitigation: Runtime .get() calls with defaults
- Recommendation: Use Pydantic models to validate config schema at load time

**Tenacity retry decorator dependency:**
- Risk: Retry logic uses custom decorator pattern not well-tested
- Impact: Unclear behavior under load or with concurrent failures
- Files: `src/fetchers/base_fetcher.py` (lines 13-19)
- Recommendation: Add integration tests for retry behavior under network failures

## Missing Critical Features

**No test suite:**
- Problem: Zero automated tests found (no pytest, unittest, etc.)
- Blocks:
  - Can't refactor with confidence
  - Can't verify bug fixes
  - Breaking changes discovered in production
- Files: Only found `templates/test_network_template.py` (template, not actual test)
- Recommendation: Start with critical paths: fetcher validation, comparison logic, Slack formatting

**No schema validation for API responses:**
- Problem: Fetchers assume API responses have expected structure; missing fields cause KeyError
- Blocks: Robust error handling, API change detection
- Files: All fetcher implementations
- Recommendation: Use Pydantic models to validate each API response shape

**No request/response logging for debugging:**
- Problem: API failures show generic errors, hard to diagnose
- Blocks: Troubleshooting integration issues
- Files: `src/fetchers/base_fetcher.py` - no logging of HTTP requests/responses
- Recommendation: Add structured logging with request/response bodies (redact secrets)

**No circuit breaker pattern:**
- Problem: If a network API is down, all fetches wait for timeout
- Blocks: Graceful degradation
- Files: Each fetcher has retry logic but no circuit breaking
- Recommendation: Implement circuit breaker to fail fast if network is consistently unavailable

**No data validation/sanity checks:**
- Problem: Negative revenues, zero ECPM, impossible deltas not caught
- Blocks: Detecting API bugs or data corruption
- Files: All fetchers, comparison logic
- Recommendation: Add validation layer post-fetch to flag anomalies

## Test Coverage Gaps

**No unit tests for comparison logic:**
- What's not tested:
  - `_calculate_delta()` with edge cases (0/0, negative values)
  - `_create_comparison_rows()` with missing platforms/ad_types
  - Date matching logic in merge operations
- Files: `main.py` (lines 91-220, 223-298), `validation_service.py` (lines 639-637)
- Risk: Percentage calculation errors, missed edge cases
- Priority: **High** - this is core business logic

**No integration tests for fetchers:**
- What's not tested:
  - Complete fetch workflow with real (sandboxed) API calls
  - Error recovery and retries
  - Session management and cleanup
- Files: All files in `src/fetchers/`
- Risk: Fetcher failures discovered only in production
- Priority: **High** - external API integration is risky

**No Slack notification format tests:**
- What's not tested:
  - Block payload structure validity
  - Table formatting with long strings
  - Threshold exceeded/normal message variations
- Files: `src/notifiers/slack_notifier.py`
- Risk: Malformed Slack messages, broken formatting
- Priority: **Medium** - affects user experience but not data accuracy

**No config validation tests:**
- What's not tested:
  - Invalid config.yaml parsing
  - Missing required keys
  - Type mismatches (string vs. int)
- Files: `src/config.py`
- Risk: Cryptic runtime errors instead of config validation errors
- Priority: **Medium** - impacts user experience

**No data export tests:**
- What's not tested:
  - GCS parquet file structure
  - Upsert behavior for duplicate dates
  - Permission errors
- Files: `src/exporters/gcs_exporter.py`
- Risk: Data corruption, silently failed exports
- Priority: **Medium** - data accuracy dependent

---

*Concerns audit: 2026-03-02*
