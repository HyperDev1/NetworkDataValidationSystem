# Coding Conventions

**Analysis Date:** 2026-03-02

## Naming Patterns

**Files:**
- Snake case with underscores: `meta_fetcher.py`, `base_fetcher.py`, `slack_notifier.py`
- Functional grouping by domain: `fetchers/`, `validators/`, `notifiers/`, `reporters/`, `exporters/`, `utils/`
- Test files follow naming pattern: `test_*.py` or `*_test.py` (e.g., `test_network_template.py`)

**Functions:**
- Snake case: `_init_ad_data()`, `get_network_name()`, `calculate_ecpm()`, `_normalize_ad_format()`
- Private/internal methods prefixed with single underscore: `_load_config()`, `_get_session()`, `_poll_async_results()`
- Method names are descriptive and action-oriented: `fetch_data()`, `close()`, `compare_metrics()`
- Async functions use same naming convention (no special prefix): `async def fetch_data()`, `async def _test_auth()`

**Variables:**
- Snake case throughout: `start_date`, `end_date`, `webhook_url`, `api_key`, `network_fetchers`
- Constants in UPPER_SNAKE_CASE: `PLATFORM_MAP`, `AD_FORMAT_MAP`, `DEFAULT_RETRY_CONFIG`, `SCOPES`
- Class attributes match constant style when static: `DEFAULT_TIMEOUT = aiohttp.ClientTimeout()`

**Types:**
- Use TypedDict for structured data definitions: `FetchResult`, `AdMetrics`, `PlatformMetrics`
- Dataclasses for configuration objects: `@dataclass class RetryConfig`
- Enums for fixed value sets: `Platform(str, Enum)`, `AdType(str, Enum)`, `NetworkName(str, Enum)`

## Code Style

**Formatting:**
- No explicit linting configuration found (no `.flake8`, `.pylintrc`, or similar)
- Uses standard Python conventions: 4-space indentation
- Single quotes for strings preferred in error messages and API endpoints; double quotes for docstrings
- Line continuations use natural break or backslash for long function signatures

**Linting:**
- No automated linting tool configured (pytest only mentioned in dependencies)
- Manual adherence to PEP 8 conventions observed throughout

**Module docstrings:**
All modules begin with triple-quoted docstring describing purpose:
```python
"""
Meta Audience Network data fetcher implementation.
Async version using aiohttp with retry support.
API Docs: https://developers.facebook.com/docs/audience-network/optimization/report-api/guide-v2/
"""
```

**Class docstrings:**
Classes have detailed docstrings explaining purpose and usage:
```python
class NetworkDataFetcher(ABC):
    """
    Abstract base class for network data fetchers.

    Provides:
    - Common data structure initialization
    - eCPM calculation
    - Platform and ad type normalization
    - Async HTTP client with retry support
    - Result building helpers
    """
```

## Import Organization

**Order:**
1. Standard library: `import sys`, `import asyncio`, `from datetime import datetime`
2. Third-party packages: `import aiohttp`, `from tenacity import retry`
3. Local modules: `from .base_fetcher import NetworkDataFetcher`, `from ..enums import Platform`
4. Conditional imports for optional features: wrapped in try/except blocks with flag

**Example from admob_fetcher.py:**
```python
import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional

from .base_fetcher import NetworkDataFetcher, FetchResult
from ..enums import Platform, AdType, NetworkName

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    Credentials = None
```

**Path Aliases:**
- Relative imports used within `src/` package: `from .base_fetcher`, `from ..enums`
- Absolute imports from root for main modules: `from src.config import Config`, `from src.fetchers import ApplovinFetcher`
- No special path alias configuration detected

## Error Handling

**Patterns:**
- Try/except blocks catch specific exceptions first, then general Exception
- Custom Exception messages include context: `raise Exception(f"Pangle API error: {str(e)}")`
- Network errors caught by exception type: `except json.JSONDecodeError`, `except HttpError`
- Retry logic uses tenacity decorator with exponential backoff:
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(SpecificError)
)
```

**Error handling in async context:**
- Try/except blocks wrap entire async operations in fetchers
- Resource cleanup using try/finally: ensure `await fetcher.close()` called
- Context managers for async resources: `async with` for session management

**Logging on error:**
```python
try:
    # operation
except Exception as e:
    logger.warning(f"Network request failed (attempt {attempt + 1}): {e}")
    raise
```

## Logging

**Framework:** Python's built-in `logging` module (not custom)

**Initialization:**
- Module-level logger instance: `logger = logging.getLogger(__name__)`
- Global configuration in `main.py`:
```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

**Patterns:**
- Info level for progress: `logger.info(f"Starting Network Comparison Report at {now_utc}...")`
- Warning level for recoverable errors: `logger.warning(f"BidMachine rate limited, waiting {wait_time}s...")`
- Debug level for initialization details: `logger.debug(f"{network_key} missing required key")`
- Context-aware messages with operation details: include dates, network names, metrics

## Comments

**When to Comment:**
- Complex algorithm logic (e.g., eCPM calculation, delta percentage handling)
- API-specific quirks and limitations (e.g., "Meta Audience Network reporting delay: Using T-1")
- Important business rules: "Only rows with |rev_delta| > threshold will be shown in Slack"
- Configuration/setup instructions in docstrings

**JSDoc/TSDoc:**
Not applicable (Python codebase). Uses Python docstring format instead:

```python
def compare_metrics(
    self,
    data1: Dict[str, Any],
    data2: Dict[str, Any],
    metrics: List[str] = ['revenue', 'impressions', 'ecpm']
) -> Dict[str, Any]:
    """
    Compare metrics between two network data sets.

    Args:
        data1: First network data
        data2: Second network data
        metrics: List of metrics to compare

    Returns:
        Dictionary containing comparison results
    """
```

## Function Design

**Size:**
- Most functions under 50 lines
- Complex async functions (like `fetch_data`) may reach 100+ lines but maintain clear structure
- Helper methods `_normalize_*`, `_parse_*`, `_build_*` typically 30-50 lines

**Parameters:**
- Maximum 5-6 parameters per function; excess uses config objects or dataclasses
- Type hints on all parameters and return values: `def __init__(self, start_date: datetime, end_date: datetime)`
- Default parameters for optional settings: `threshold_percentage: float = 5.0`
- Async functions have same parameter structure as sync equivalents

**Return Values:**
- Single return value preferred; complex structures use TypedDict or dataclass
- Async functions return typed results: `async def fetch_data(...) -> FetchResult`
- Methods returning status use bool, dict, or None:
```python
async def _test_auth(self) -> bool:
async def compare_metrics(...) -> Dict[str, Any]:
```

## Module Design

**Exports:**
- Modules explicitly export classes/functions through imports in `__init__.py` files
- Example from `src/fetchers/__init__.py`: exposes fetcher classes for factory pattern use
- Base classes and utilities available for inheritance and composition

**Barrel Files:**
- `__init__.py` files used strategically in `fetchers/`, `notifiers/`, `reporters/`, `exporters/`, `validators/`, `utils/`
- Keep imports minimal; avoid circular imports by using type hints

**Example from src/__init__.py:**
```python
# Minimal - only essential imports
```

**Architecture pattern:**
- Factory pattern: `FetcherFactory` creates network-specific fetcher instances
- Abstract base class: `NetworkDataFetcher` defines interface for all fetchers
- Strategy pattern: Different error handling strategies per network (e.g., Pangle vs Meta)
- Service pattern: `ValidationService` orchestrates fetchers and notifiers

---

*Convention analysis: 2026-03-02*
