# Technology Stack

**Analysis Date:** 2026-03-02

## Languages

**Primary:**
- Python 3.13.5 - Core application logic for data fetching, validation, and export

**Secondary:**
- YAML - Configuration file format for all settings and secrets

## Runtime

**Environment:**
- Python 3.13.5 (defined in `Pipfile` and `requirements.txt`)

**Package Manager:**
- pip - Primary package installation
- Pipenv - Virtual environment management via `Pipfile`

## Frameworks

**Core:**
- aiohttp 3.9.0+ - Async HTTP client for network API requests with retry support
- requests 2.28.0+ - Synchronous HTTP client for legacy integrations

**Data & Configuration:**
- PyYAML 6.0+ - Configuration file parsing in `src/config.py`
- Pydantic 2.5.0+ - Data validation and settings management

**API Clients:**
- google-api-python-client 2.100.0+ - Google AdMob and Google APIs access
- google-auth 2.22.0+ - OAuth 2.0 authentication for Google services
- google-auth-oauthlib - OAuth 2.0 flow for browser-based authentication (AdMob)
- google-cloud-storage 2.14.0+ - GCS client for data export
- google-cloud-bigquery 3.14.0+ - BigQuery integration for analytics

**Scheduling & Process Management:**
- schedule 1.2.0+ - Cron-like task scheduling in `service.py`
- psutil 5.9.0+ - Process and system resource monitoring

**Utilities:**
- tabulate 0.9.0+ - Table formatting for console output in reports
- tenacity 8.2.0+ - Retry logic with exponential backoff for API calls

**Data Processing:**
- pandas - DataFrame operations for data transformation
- PyArrow 14.0.0+ - Arrow format for efficient Parquet serialization
- pyarrow.parquet - Parquet file writing/reading for GCS export

## Key Dependencies

**Critical:**
- `aiohttp` - Enables async HTTP requests for efficient concurrent API calls across multiple ad networks
- `google-cloud-storage` - Handles Parquet file export to GCS for BigQuery analysis
- `google-api-python-client` - Powers AdMob and Google APIs integration
- `tenacity` - Provides exponential backoff retry logic essential for flaky network APIs

**Infrastructure:**
- `google-auth` - OAuth 2.0 authentication framework for all Google services
- `PyYAML` - Configuration parsing supporting nested access patterns (e.g., `config.get('slack.webhook_url')`)
- `requests` - Fallback HTTP client for services requiring synchronous API calls

**Data Processing:**
- `pandas` - Data manipulation and filtering for comparison operations
- `pyarrow` + `pyarrow.parquet` - Columnar storage format with schema enforcement

## Configuration

**Environment:**
- Configuration via YAML file: `config.yaml` (copied from `config.yaml.example`)
- Loaded in `src/config.py` using `Config` class with nested key access
- Supports optional GCP service account authentication via `service_account_path`

**Key configs required:**
- `applovin.api_key` - AppLovin MAX API authentication
- `slack.webhook_url` - Slack alert notifications
- `gcp.project_id` and `gcp.bucket_name` - GCS export target
- Network-specific configs: `admob`, `meta`, `unity`, `mintegral`, `ironsource`, `liftoff`, `dt_exchange`, `pangle`, `bidmachine`, `inmobi`, `moloco`

**Build:**
- No build configuration required (pure Python)
- Virtual environment: `Pipfile` for development setup
- Dependencies: `requirements.txt` for production deployments

## Platform Requirements

**Development:**
- Python 3.13.5
- pip and Pipenv for dependency management
- GCP SDK (optional, for testing GCS export)
- Google OAuth 2.0 credentials JSON for AdMob testing

**Production:**
- Python 3.13.5 runtime
- GCP Service Account with:
  - Cloud Storage (GCS) read/write permissions
  - BigQuery read/write permissions (if using BigQuery export)
- Network connectivity to:
  - AppLovin MAX API (`r.applovin.com`)
  - Ad network APIs (Meta, Google, Unity, Mintegral, IronSource, Liftoff, DT Exchange, Pangle, etc.)
  - Slack API (webhook endpoint)
  - Google Cloud APIs

---

*Stack analysis: 2026-03-02*
