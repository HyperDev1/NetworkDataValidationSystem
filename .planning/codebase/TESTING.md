# Testing Patterns

**Analysis Date:** 2026-03-02

## Test Framework

**Runner:**
- No automated test runner configured (pytest, unittest, or vitest not in requirements)
- Manual/scripted testing approach used via test template files

**Test Assertion Library:**
- Built-in Python assertions where needed
- No dedicated testing library dependencies found

**Run Commands:**
```bash
# Run main validation service
python main.py

# Run validation service with date range backfill
python main.py --start_date 2024-01-01 --end_date 2024-01-31

# Run as scheduled service (continuous loop with retry)
python main.py --schedule

# Async test of individual network fetcher
python templates/test_network_template.py --auth-only
python templates/test_network_template.py --full-fetch
```

## Test File Organization

**Location:**
- Test templates in `templates/` directory: `templates/test_network_template.py`
- Main integration tests embedded in `main.py` execution
- No unit test files found in codebase; testing is manual/ad-hoc

**Naming:**
- Test files use `test_` prefix: `test_network_template.py`
- Script-based tests match module names: test scripts for each fetcher implementation

**Structure:**
```
templates/
├── test_network_template.py        # Template for testing individual fetcher
scripts/
├── fix_bigquery_table.py          # Utility scripts
├── migrate_gcs_network_names.py
└── migrate_network_names.py
```

## Test Structure

**Test Template Organization:**
Template in `templates/test_network_template.py` shows standard test flow:

```python
async def main():
    """Main async test function."""

    # Step 1: Load Configuration
    config = Config()
    network_config = config.get_networkname_config()

    # Step 2: Check Credentials
    if not check_credentials(network_config):
        print("\n   ❌ Please update credentials in config.yaml")
        return

    # Step 3: Initialize Fetcher
    fetcher = NetworkNameFetcher(
        api_key=network_config['api_key'],
        publisher_id=network_config['publisher_id'],
    )

    # Step 4: Auth Test
    if hasattr(fetcher, '_test_auth'):
        auth_success = await fetcher._test_auth()
        if not auth_success:
            print("\n   ❌ Auth test failed")
            return

    # Step 5: Report Test
    data = await fetcher.fetch_data(start_date, end_date)
    print_results(data)

    # Cleanup
    await fetcher.close()
```

**Patterns:**
- Configuration loading: Read YAML config and validate it contains required fields
- Credential validation: Check for placeholder values, missing fields
- Initialization: Create fetcher with config-provided credentials
- Auth testing: Call optional `_test_auth()` method if available
- Data fetch: Call `fetch_data()` with date range
- Result display: Format and print returned metrics in readable format
- Cleanup: Always call `await fetcher.close()` to close HTTP session

## Mocking

**Framework:**
- No explicit mocking library used (unittest.mock not in dependencies)
- Manual test methods in fetchers serve as test doubles: `_test_auth()`, `_test_report_request()`

**Patterns:**
Test methods provided by fetchers for isolated testing without real API calls:

```python
if hasattr(fetcher, '_test_auth'):
    auth_success = await fetcher._test_auth()

if hasattr(fetcher, '_test_report_request') and not full_fetch:
    response_data = await fetcher._test_report_request(start_date, end_date)
```

**What to Mock:**
- HTTP requests to external APIs (e.g., Meta, AdMob, etc.)
- Credential validation if testing auth flow without real credentials
- Time-dependent operations (use fixed dates rather than `datetime.now()`)

**What NOT to Mock:**
- Configuration loading (use actual config.yaml for integration tests)
- Data parsing logic (test with real API response structures)
- Error handling paths (test actual exception types from APIs)

## Fixtures and Factories

**Test Data:**
No dedicated fixture framework. Test data created inline in test templates:

```python
end_date = datetime.now(timezone.utc) - timedelta(days=1)
start_date = end_date

# Create fetcher with test credentials from config
fetcher = NetworkNameFetcher(
    api_key=network_config['api_key'],
    publisher_id=network_config['publisher_id'],
)
```

**Location:**
- Shared test data in `templates/test_network_template.py` (template form)
- Configuration fixtures in `config.yaml` (actual config file)
- Sample response structures documented in fetcher files as constants

**Example response structure from meta_fetcher.py:**
```python
# AD_FORMAT_MAP shows expected API field mappings
AD_FORMAT_MAP = {
    'banner': AdType.BANNER,
    'medium_rectangle': AdType.BANNER,
    'interstitial': AdType.INTERSTITIAL,
    'rewarded_video': AdType.REWARDED,
    'rewarded_interstitial': AdType.REWARDED,
}
```

## Coverage

**Requirements:**
- No automated coverage measurement configured
- Manual verification through test template execution

**View Coverage:**
```bash
# Coverage is manual: run test_network_template.py and inspect output
python templates/test_network_template.py --full-fetch

# Output shows:
# - ✅ Credential check passed
# - ✅ Auth test passed
# - ✅ Data fetch completed with metric breakdown
# - ✅ Platform-level breakdown (Android/iOS)
# - ✅ Ad-type breakdown (banner/interstitial/rewarded)
```

## Test Types

**Unit Tests:**
- Not formally organized as unit tests
- Individual function testing: `calculate_ecpm()`, `parse_delta_percentage()`, `format_delta()` in `utils/calculations.py`
- Can be tested inline in Python REPL or simple script

Example from docstrings:
```python
def calculate_ecpm(revenue: float, impressions: int) -> float:
    """
    Calculate eCPM (effective Cost Per Mille) from revenue and impressions.

    Example:
        >>> calculate_ecpm(100.0, 50000)
        2.0
        >>> calculate_ecpm(0.0, 1000)
        0.0
    """
```

**Integration Tests:**
- Full workflow tested via `main.py` execution
- Tests entire pipeline: config load → fetch all networks → validate data → export to GCS → send Slack notification
- Validates network fetchers against real APIs (with valid credentials)
- Tests data comparison logic in `ValidationService.run_validation()`

```python
# From main.py - integration test
async def main(args):
    config = Config()
    service = ValidationService(config)

    # Run full pipeline
    report = await service.run_validation(
        start_date=args.start_date,
        end_date=args.end_date,
        no_slack=args.no_slack_message
    )
```

**E2E Tests:**
- Not formally defined as E2E tests
- Manual E2E via `python main.py --schedule` for continuous runs
- Validates full system behavior including scheduling, retry logic, Slack notifications

## Common Patterns

**Async Testing:**
All network fetchers use async/await pattern:

```python
async def test_fetcher():
    fetcher = NetworkFetcher(credentials)
    try:
        data = await fetcher.fetch_data(start_date, end_date)
        assert data['revenue'] > 0
        print("✅ Fetch successful")
    finally:
        await fetcher.close()

# Run with asyncio
asyncio.run(test_fetcher())
```

**Error Testing:**
Errors validated through template test execution:

```python
try:
    auth_success = await fetcher._test_auth()
    if not auth_success:
        print("\n   ❌ Auth test failed - fix credentials before continuing")
        return
except Exception as e:
    print_separator("❌ TEST FAILED", "=")
    print(f"\n   Error: {str(e)}")
    import traceback
    traceback.print_exc()
finally:
    await fetcher.close()
    print("\n   🔒 Session closed")
```

**Data Validation Testing:**
Validator tested through `DataValidator.compare_metrics()`:

```python
from src.validators.data_validator import DataValidator

validator = DataValidator(threshold_percentage=5.0)
results = validator.compare_metrics(data1, data2, metrics=['revenue', 'impressions', 'ecpm'])

# Validate results structure
assert 'has_discrepancy' in results
assert 'discrepancies' in results
assert all('metric' in d for d in results['discrepancies'])
```

**Test Environment:**
- Uses real API credentials from `config.yaml`
- Tests against actual external API endpoints (no sandbox mode documented)
- Requires network connectivity for real API calls
- Test isolation: each fetcher test is independent, can run individually

## Testing Workflow

**Standard test procedure for new network:**

1. Copy `templates/test_network_template.py` and update for new network
2. Update import: `from src.fetchers.networkname_fetcher import NetworkNameFetcher`
3. Update config method: `config.get_networkname_config()`
4. Update required credentials: `required_fields = ['api_key', 'publisher_id']`
5. Update fetcher initialization with network-specific parameters
6. Run: `python test_networkname.py --auth-only` (verify credentials work)
7. Run: `python test_networkname.py --full-fetch` (verify data retrieval)
8. Verify output structure includes all expected metrics (revenue, impressions, eCPM, platform/ad-type breakdown)

---

*Testing analysis: 2026-03-02*
