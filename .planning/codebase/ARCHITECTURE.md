# Architecture

**Analysis Date:** 2026-03-02

## Pattern Overview

**Overall:** Event-driven pipeline with async orchestration and pluggable data sources.

**Key Characteristics:**
- **Async-first design** using `asyncio` for parallel network data fetching (~5-8s vs ~30-60s sequential)
- **Layered architecture** separating data fetching, validation, and notification concerns
- **Factory pattern** for fetcher instantiation, allowing easy network additions
- **Enum-based typing** for platforms, ad types, and network names (type safety)
- **Multi-stage pipeline** with distinct transformation phases (fetch → merge → calculate → report)

## Layers

**Data Fetching Layer:**
- Purpose: Retrieve revenue and impression data from external APIs (AppLovin MAX and ad networks)
- Location: `src/fetchers/`
- Contains: Base fetcher interface, 12 network-specific fetcher implementations
- Depends on: Configuration, enums for data normalization
- Used by: ValidationService orchestrator

**Configuration Layer:**
- Purpose: YAML-based runtime configuration management with nested key access
- Location: `src/config.py`
- Contains: Config class with getters for applovin, networks, slack, gcp, scheduling
- Depends on: External YAML file, environment
- Used by: ValidationService, FetcherFactory, Slack notifier

**Enum/Type Layer:**
- Purpose: Type-safe constants and bidirectional mappings between API formats and internal representations
- Location: `src/enums.py`
- Contains: Platform (android/ios), AdType (banner/interstitial/rewarded), NetworkName enums
- Depends on: None (leaf module)
- Used by: Fetchers, validators, reporters for normalization

**Validation/Orchestration Layer:**
- Purpose: Central orchestrator coordinating data fetching, merging, and comparison
- Location: `src/validation_service.py`
- Contains: ValidationService class with async workflow methods
- Depends on: Fetchers, config, notifiers, exporters
- Used by: main.py and service.py entry points

**Notification Layer:**
- Purpose: Format and send comparison reports to external systems (Slack, GCS)
- Location: `src/notifiers/slack_notifier.py`, `src/exporters/gcs_exporter.py`
- Contains: SlackNotifier for Slack messages, GCSExporter for cloud storage
- Depends on: Slack API, GCP SDK
- Used by: ValidationService after data comparison

**Utility/Support Layer:**
- Purpose: Shared utilities for token caching, calculations, and data validation
- Location: `src/utils/`, `src/validators/`
- Contains: Token cache (file-based TTL), calculation helpers, data validators
- Depends on: None (self-contained)
- Used by: Fetchers and service logic

## Data Flow

**Main Validation Workflow:**

1. **Configuration Loading** (`main.py` → `Config()`)
   - Loads YAML configuration with API credentials, thresholds, scheduling

2. **Parallel Data Fetching** (`ValidationService.run_validation()`)
   - Fetches AppLovin MAX data (baseline) for date range
   - Simultaneously fetches from all enabled networks using `asyncio.gather()`
   - Each fetcher normalizes data to `daily_data[date][platform][ad_type]` structure
   - Returns aggregated revenue/impressions and platform breakdown

3. **Data Merging** (`_merge_data()`)
   - Joins MAX rows with corresponding network data by date/platform/ad_type
   - Calculates deltas: revenue%, impressions%, eCPM%
   - Includes all MAX rows even if network data missing (sets values to None)
   - Produces `comparison_rows` for both Slack and GCS export

4. **Report Generation** (two paths):
   - **Slack Path**: Filters by threshold (revenue_delta_threshold), min_revenue_for_alerts
   - **GCS Path**: Exports all comparison rows to Parquet for BigQuery/Looker

5. **Notification** (`SlackNotifier.send_comparison_report()`)
   - Sends formatted Slack message with per-network summaries
   - Includes placement breakdown (app × ad_type matrix)

**State Management:**
- **Transient state**: Network data held in memory during single validation run
- **Persistent state**: Token cache on disk (`credentials/` dir)
- **External state**: Comparison data in GCS buckets (immutable append-only)

## Key Abstractions

**NetworkDataFetcher:**
- Purpose: Base interface for all network API integrations
- Examples: `src/fetchers/meta_fetcher.py`, `src/fetchers/unity_fetcher.py`
- Pattern: Abstract class with `fetch_data(start_date, end_date)` → `Dict[str, Any]` contract
- Implementation: Each fetcher handles API-specific auth, request format, response parsing

**FetcherFactory:**
- Purpose: Centralized instantiation of network fetchers from config
- Examples: Used in `ValidationService._initialize_network_fetchers()`
- Pattern: Static factory with registry (network_key → {class, config_mapper})
- Benefit: Decouples fetcher availability from orchestrator logic

**NetworkName Enum:**
- Purpose: Bidirectional mapping between AppLovin API names and internal identifiers
- Examples: `'Facebook Bidding'` → `NetworkName.META` → `'meta'`
- Pattern: `from_api_name()` for normalization, `value` for internal key, `display_name` for UI
- Benefit: Single source of truth for network identification across all layers

## Entry Points

**main.py:**
- Location: `main.py`
- Triggers: Direct Python execution or scheduler
- Responsibilities: CLI parsing, date range calculation, async workflow orchestration
- Key functions: `run_validation()` (async), `run_single_validation()`, `run_scheduled()`

**service.py:**
- Location: `service.py`
- Triggers: Windows service control or supervisor
- Responsibilities: Process lifecycle management (start/stop/restart), PID tracking
- Key functions: `start_service()`, `stop_service()`, `status_service()`

**Scheduled Mode:**
- Location: `main.py:run_scheduled()`
- Triggers: Time-based (configured scheduled_times from config.yaml)
- Responsibilities: Loop with 30-second check interval, trigger validation at scheduled times
- Key flow: Check current time → match scheduled time → run validation → sleep 30s

## Error Handling

**Strategy:** Graceful degradation with partial results.

**Patterns:**
- **Fetcher-level**: Try-except with logging, return `(network_key, None)` on failure
- **Parallel fetch**: `asyncio.gather(*tasks, return_exceptions=True)` collects all results/errors
- **Failed networks**: Tracked in `network_data['_failed_networks']` list, shown in Slack
- **Missing network data**: Comparison rows include NULL values, marked `has_network_data=False`
- **API retry**: Tenacity decorator with exponential backoff (max 3 attempts, 1-10s wait)

**Example flow:**
```python
# If network API fails, ValidationService still completes
# Slack message shows: "Failed networks: meta, dt_exchange"
# GCS export includes MAX data even for failed networks (NULL network columns)
```

## Cross-Cutting Concerns

**Logging:**
- Framework: Python `logging` module
- Approach: Each module has `logger = logging.getLogger(__name__)`
- Configuration: `basicConfig()` in main.py (INFO level, ISO format timestamps)
- Usage: Progress indicators, error tracking, performance metrics (timing)

**Validation:**
- Approach: Data validators check impressions > 0, revenue > 0 before including in comparisons
- Location: `src/validators/data_validator.py`
- Applied at: Each fetcher output, merge stage

**Authentication:**
- Approach: Credentials from `config.yaml` (YAML file not committed to git)
- Token caching: File-based TTL cache for OAuth tokens in `src/utils/token_cache.py`
- Applied in: Meta, AdMob, and other OAuth-based fetchers

**Date Handling:**
- Approach: UTC timezone throughout, date normalization using `Platform.from_string()`, `AdType.from_string()`
- Special cases: Meta has 2-day delay (T-2), DT Exchange has variable delay (T-1 to T-2)
- Applied in: `ValidationService` date range calculations, fetcher-specific overrides

---

*Architecture analysis: 2026-03-02*
