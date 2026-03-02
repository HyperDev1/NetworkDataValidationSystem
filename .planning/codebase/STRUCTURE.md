# Codebase Structure

**Analysis Date:** 2026-03-02

## Directory Layout

```
NetworkDataValidationSystem/
├── main.py                        # Entry point: async validation orchestrator
├── service.py                     # Service controller: start/stop/restart/status
├── config.yaml.example            # Configuration template (copy to config.yaml)
├── config.yaml                    # Runtime configuration (git-ignored)
├── requirements.txt               # Python dependencies
├── Pipfile / Pipfile.lock         # Pipenv lock file
├── README.md                      # User documentation
├── AGENT.md                       # AI agent documentation
├── SKILLS.md                      # Procedural skills documentation
├── .planning/codebase/            # GSD codebase analysis documents
├── credentials/                   # OAuth tokens and service account keys (git-ignored)
│   ├── token_cache.json           # Token cache for OAuth
│   └── admob-service-account.json # GCP service account
├── src/
│   ├── __init__.py
│   ├── config.py                  # Configuration loader (YAML parser)
│   ├── enums.py                   # Type-safe enums (Platform, AdType, NetworkName)
│   ├── validation_service.py      # Main orchestrator for validation workflow
│   ├── fetchers/                  # Network data fetchers (12 implementations)
│   │   ├── __init__.py
│   │   ├── base_fetcher.py        # Abstract base class with async/retry support
│   │   ├── factory.py             # Fetcher factory (registry pattern)
│   │   ├── applovin_fetcher.py    # AppLovin MAX data (baseline)
│   │   ├── admob_fetcher.py       # Google AdMob API
│   │   ├── meta_fetcher.py        # Meta Audience Network (2-day delay)
│   │   ├── unity_fetcher.py       # Unity Ads API
│   │   ├── mintegral_fetcher.py   # Mintegral API
│   │   ├── ironsource_fetcher.py  # IronSource API
│   │   ├── inmobi_fetcher.py      # InMobi API
│   │   ├── moloco_fetcher.py      # Moloco API
│   │   ├── bidmachine_fetcher.py  # BidMachine API
│   │   ├── liftoff_fetcher.py     # Liftoff (Vungle) API
│   │   ├── dt_exchange_fetcher.py # DT Exchange (Fyber) API
│   │   └── pangle_fetcher.py      # Pangle (TikTok) API
│   ├── exporters/                 # Data export destinations
│   │   ├── __init__.py
│   │   └── gcs_exporter.py        # Google Cloud Storage (Parquet format)
│   ├── notifiers/                 # External notifications
│   │   ├── __init__.py
│   │   └── slack_notifier.py      # Slack message formatting and sending
│   ├── validators/                # Data validation logic
│   │   ├── __init__.py
│   │   └── data_validator.py      # Impression/revenue validation
│   ├── reporters/                 # Report generation
│   │   ├── __init__.py
│   │   └── table_reporter.py      # Formatted table output
│   └── utils/                     # Shared utilities
│       ├── __init__.py
│       ├── token_cache.py         # File-based token caching (TTL)
│       └── calculations.py        # eCPM, delta calculations
├── templates/                     # Code templates for new networks
│   ├── network_fetcher_template.py  # Skeleton for new fetcher
│   ├── test_network_template.py     # Skeleton for fetcher tests
│   └── api_analysis_checklist.md    # Guide for analyzing new APIs
├── scripts/                       # Database and utility scripts
│   ├── fix_bigquery_table.py
│   ├── migrate_gcs_network_names.py
│   ├── migrate_network_names.py
│   └── update_views.py
└── docs/
    └── tables/                    # BigQuery schema documentation
        ├── network_comparison.md  # Comparison table schema
        ├── network_data_availability.md
        └── sync_metadata.md
```

## Directory Purposes

**Project Root:**
- Purpose: Project configuration and entry points
- Contains: main.py (async orchestrator), service.py (service control), config files
- Key files: `main.py` (5000+ lines, handles 6 workflow steps), `service.py` (305 lines, process management)

**src/:**
- Purpose: Core application code
- Contains: Configuration, enums, fetchers, exporters, notifiers
- Key files: `validation_service.py` (700+ lines, async orchestration), `config.py` (100+ lines, YAML parsing)

**src/fetchers/:**
- Purpose: Network-specific data retrieval
- Contains: 12 fetcher implementations + base class + factory
- Key files: `base_fetcher.py` (base interface), `factory.py` (dependency injection), `applovin_fetcher.py` (baseline MAX data)
- Pattern: Each fetcher extends `NetworkDataFetcher`, implements `fetch_data(start_date, end_date)` → normalized dict

**src/exporters/:**
- Purpose: Export comparison data to external storage
- Contains: GCS exporter for Parquet files
- Key files: `gcs_exporter.py` (Parquet schema + GCS upload)

**src/notifiers/:**
- Purpose: Send alerts and reports externally
- Contains: Slack notifier with formatting logic
- Key files: `slack_notifier.py` (message formatting, webhook posting)

**src/validators/:**
- Purpose: Data quality checks
- Contains: Data validation rules
- Key files: `data_validator.py` (impressions > 0, revenue > 0 checks)

**src/reporters/:**
- Purpose: Terminal and dashboard reporting
- Contains: Table formatting for console output
- Key files: `table_reporter.py` (ASCII table generation)

**src/utils/:**
- Purpose: Shared helper functions
- Contains: Token caching, calculations
- Key files: `token_cache.py` (file-based TTL), `calculations.py` (eCPM formulas)

**credentials/:**
- Purpose: Runtime authentication secrets (git-ignored)
- Contains: OAuth tokens, GCP service account JSON files
- Key files: `token_cache.json` (Meta/AdMob tokens), `admob-service-account.json` (GCP auth)

**templates/:**
- Purpose: Scaffolding for adding new networks
- Contains: Code skeletons and procedural guides
- Key files: `network_fetcher_template.py` (minimal fetcher), `api_analysis_checklist.md` (procedure)

**scripts/:**
- Purpose: One-off data migration and maintenance
- Contains: BigQuery schema migration, network name normalization
- Key files: Network name mapping scripts

**docs/:**
- Purpose: BigQuery schema and metadata documentation
- Contains: Table schemas for Looker
- Key files: `network_comparison.md` (schema reference)

## Key File Locations

**Entry Points:**
- `main.py`: Validation orchestrator (async workflow, scheduling, CLI)
- `service.py`: Service lifecycle control (start/stop/status)

**Configuration:**
- `config.yaml`: Runtime configuration (credentials, thresholds, scheduling)
- `config.yaml.example`: Configuration template

**Core Logic:**
- `src/validation_service.py`: Async orchestration (fetch → merge → report)
- `src/config.py`: YAML configuration parser
- `src/enums.py`: Type-safe constants and bidirectional mappings

**Data Fetching:**
- `src/fetchers/base_fetcher.py`: Abstract interface for all fetchers
- `src/fetchers/factory.py`: Fetcher registry and instantiation
- `src/fetchers/applovin_fetcher.py`: AppLovin MAX (baseline data source)
- `src/fetchers/{network}_fetcher.py`: 11 other network implementations

**External Integration:**
- `src/notifiers/slack_notifier.py`: Slack message formatting and sending
- `src/exporters/gcs_exporter.py`: Google Cloud Storage (Parquet export)

**Testing:**
- `templates/test_network_template.py`: Fetcher test template (copy for new networks)

## Naming Conventions

**Files:**
- Fetcher files: `{network_name}_fetcher.py` (lowercase, underscores)
  - Examples: `meta_fetcher.py`, `unity_fetcher.py`, `dt_exchange_fetcher.py`
- Supporting modules: `{purpose}.py` (lowercase, semantic naming)
  - Examples: `token_cache.py`, `data_validator.py`, `table_reporter.py`

**Directories:**
- Feature modules: lowercase plural `{feature}/` (e.g., `fetchers/`, `validators/`, `notifiers/`)
- Shared data: lowercase `credentials/`, `templates/`, `docs/`

**Classes:**
- Fetcher classes: `{NetworkName}Fetcher` (PascalCase, specific suffix)
  - Examples: `MintegralFetcher`, `UnityAdsFetcher`, `MetaFetcher`
- Other classes: `{Purpose}{Type}` (PascalCase)
  - Examples: `ValidationService`, `SlackNotifier`, `GCSExporter`

**Functions:**
- Public methods: `{verb}_{noun}` (snake_case)
  - Examples: `fetch_data()`, `send_message()`, `export_multi_day()`
- Private methods: `_{verb}_{noun}` (leading underscore)
  - Examples: `_fetch_all_networks_parallel()`, `_merge_data()`, `_calculate_delta()`

**Constants/Enums:**
- Enum values: UPPERCASE (e.g., `Platform.ANDROID`, `AdType.REWARDED`)
- Map constants: UPPERCASE_SUFFIX_MAP (e.g., `NETWORK_DISPLAY_NAME_MAP`, `FETCHER_REGISTRY`)

## Where to Add New Code

**New Feature (e.g., new metric calculation):**
- Primary code: `src/utils/calculations.py` (calculation logic) or `src/validators/data_validator.py` (if validation)
- Tests: Create `test_{feature}.py` in project root (follow pytest convention)

**New Ad Network Integration:**
- Fetcher implementation: `src/fetchers/{network_name}_fetcher.py`
- Factory registration: Add entry to `FETCHER_REGISTRY` in `src/fetchers/factory.py`
- Config mapping: Add network config accessor to `src/config.py` (e.g., `get_{network}_config()`)
- Enum: Add `NetworkName.{NETWORK}` to `src/enums.py`
- Test script: `test_{network_name}.py` in project root (use template)

**New External Integration (Slack alternative, new data export destination):**
- Notifier: `src/notifiers/{service}_notifier.py` (follows `SlackNotifier` interface)
- Exporter: `src/exporters/{destination}_exporter.py` (follows `GCSExporter` interface)
- Config: Add getters to `src/config.py`
- Integration: Call in `validation_service.py` alongside existing notifiers/exporters

**Utilities and Helpers:**
- Shared helpers: `src/utils/{purpose}.py` (e.g., `src/utils/http_client.py` for shared HTTP logic)
- Validation rules: `src/validators/{rule_type}.py` (follows `data_validator.py` pattern)
- Report generators: `src/reporters/{format}_reporter.py` (follows `table_reporter.py` pattern)

## Special Directories

**credentials/:**
- Purpose: Runtime authentication and secrets (never committed)
- Generated: Yes (created on first OAuth flow or manual placement)
- Committed: No (.gitignore entry)
- Content: Service account JSONs, token cache files with TTL

**scripts/:**
- Purpose: One-off maintenance and data migration
- Generated: No (pre-written)
- Committed: Yes (version control for reproducibility)
- Content: BigQuery schema fixes, network name migrations

**templates/:**
- Purpose: Scaffolding for new network integrations
- Generated: No (pre-written)
- Committed: Yes (reference material)
- Content: Fetcher skeleton, test skeleton, API analysis checklist

**docs/:**
- Purpose: BigQuery schema and Looker documentation
- Generated: No (manually maintained)
- Committed: Yes
- Content: Table schemas, column descriptions, partition strategies

---

*Structure analysis: 2026-03-02*
