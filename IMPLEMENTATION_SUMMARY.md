# Network Data Validation System - Implementation Summary

## Overview
A complete validation system for comparing revenue and impression data across multiple ad networks (Adjust, Applovin Max, etc.) with automated Slack notifications for discrepancies.

## Problem Statement (Turkish)
Bir validation sistemi kurmak istiyorum. Amacı Adjust, Applovin Max ve mediation için kullandığım diğer networklerden revenue impression verilerini çekip karşılaştırma yapacak. Belirlenen hata payı üzerinde bir fark çıkıyor ise bunu slack üzerinden belirlediğimiz kanala yazacak. Aynı zamanda bu işlemi belirlediğim periyotlar aralığında sürekli kendisi yapacak.

## Translation
"I want to set up a validation system. Its purpose is to fetch revenue and impression data from Adjust, Applovin Max, and other networks I use for mediation and make comparisons. If a difference above the specified error margin is detected, it will post this to the Slack channel we specify. It will also continuously perform this operation at intervals I determine."

## Solution Implemented

### Architecture
The system is built with Python using a modular architecture:

```
src/
├── config.py                 # Configuration management
├── validation_service.py     # Main orchestration service
├── fetchers/                 # Network data fetchers
│   ├── base_fetcher.py      # Abstract base class
│   ├── adjust_fetcher.py    # Adjust API integration
│   └── applovin_fetcher.py  # Applovin Max API integration
├── validators/               # Data validation logic
│   └── data_validator.py    # Comparison and threshold checking
└── notifiers/                # Notification systems
    └── slack_notifier.py    # Slack webhook integration
```

### Key Features

#### 1. Multi-Network Data Fetching
- **Adjust Integration**: Fetches revenue and impression data using Adjust KPIs API
- **Applovin Max Integration**: Fetches data using Applovin reporting API
- **Extensible Design**: Easy to add new networks by extending `NetworkDataFetcher` base class

#### 2. Intelligent Data Validation
- Compares metrics (revenue, impressions) between networks
- Calculates percentage differences with proper edge case handling:
  - Both values zero: 0% difference
  - Baseline zero, comparison non-zero: ∞% difference (automatically flagged)
  - Normal case: Standard percentage calculation
- Configurable threshold (default: 5%)
- Compares multiple networks against a baseline

#### 3. Slack Notifications
- Rich formatted messages with:
  - Alert header with warning emoji
  - Date range and timestamp
  - Detailed comparison for each metric
  - Properly formatted values (currency for revenue, thousands separator for impressions)
  - Percentage differences with special handling for infinity
- Test mode to verify integration
- Configurable channel

#### 4. Scheduling System
- Periodic validation checks (configurable interval, default: 6 hours)
- Three execution modes:
  - Continuous: Runs with periodic scheduling
  - One-time: Single validation check
  - Test: Verify Slack integration
- Graceful shutdown with Ctrl+C

#### 5. Configuration Management
- YAML-based configuration for:
  - API credentials (never committed to git)
  - Validation thresholds
  - Metrics to compare
  - Date range settings
  - Scheduling intervals
- Example configuration provided

### Files Created

1. **main.py** - Entry point with command-line interface
2. **config.yaml.example** - Configuration template
3. **requirements.txt** - Python dependencies
4. **.gitignore** - Excludes sensitive files
5. **src/config.py** - Configuration loader
6. **src/validation_service.py** - Main orchestration service
7. **src/fetchers/base_fetcher.py** - Abstract fetcher interface
8. **src/fetchers/adjust_fetcher.py** - Adjust API integration
9. **src/fetchers/applovin_fetcher.py** - Applovin Max integration
10. **src/validators/data_validator.py** - Comparison logic
11. **src/notifiers/slack_notifier.py** - Slack notifications
12. **test_system.py** - Comprehensive test suite
13. **README.md** - Complete documentation

### Usage Examples

```bash
# Run continuously with scheduling
python main.py

# Run once and exit
python main.py --once

# Test Slack integration
python main.py --test-slack

# Show help
python main.py --help
```

### Configuration Example

```yaml
adjust:
  api_token: "YOUR_ADJUST_API_TOKEN"
  app_token: "YOUR_ADJUST_APP_TOKEN"

applovin:
  api_key: "YOUR_APPLOVIN_API_KEY"
  package_name: "YOUR_PACKAGE_NAME"

slack:
  webhook_url: "YOUR_SLACK_WEBHOOK_URL"
  channel: "#revenue-alerts"

validation:
  threshold_percentage: 5.0  # 5% threshold
  metrics:
    - revenue
    - impressions
  date_range_days: 1

scheduling:
  interval_hours: 6  # Check every 6 hours
  enabled: true
```

### Testing

Comprehensive test suite (`test_system.py`) includes:
- Data validation logic tests
- Slack message formatting tests
- Multiple network comparison tests
- Edge case handling (zero baseline values)
- All tests pass successfully

### Security

- ✅ No security vulnerabilities detected (CodeQL scan)
- Configuration file with secrets excluded from git
- No hardcoded credentials
- Input validation and error handling
- Proper exception handling for API failures

### Extensibility

Adding a new network is straightforward:

1. Create new fetcher class extending `NetworkDataFetcher`
2. Implement `fetch_data()` and `get_network_name()` methods
3. Add configuration section in `config.yaml`
4. Register fetcher in `ValidationService._initialize_components()`

### Documentation

- Complete README.md with:
  - Installation instructions
  - Usage examples
  - Configuration guide
  - Troubleshooting section
  - Extension guide
- Inline code documentation
- Example configuration file

## Requirements Met

✅ **Data Fetching**: Fetches revenue and impression data from Adjust, Applovin Max  
✅ **Comparison**: Compares data and calculates differences  
✅ **Threshold Detection**: Detects when differences exceed configured threshold  
✅ **Slack Notifications**: Sends alerts to Slack when discrepancies found  
✅ **Periodic Execution**: Runs continuously at configured intervals  
✅ **Configuration**: Fully configurable via YAML  
✅ **Extensibility**: Easy to add new networks  

## Code Quality

- Modular, maintainable architecture
- Comprehensive error handling
- Pythonic code style
- Type hints for better IDE support
- Well-documented with docstrings
- No security vulnerabilities
- All tests passing

## Next Steps for Users

1. Copy `config.yaml.example` to `config.yaml`
2. Add API credentials for Adjust and Applovin Max
3. Configure Slack webhook URL
4. Adjust threshold and scheduling settings as needed
5. Run with `python main.py`
6. Monitor Slack for discrepancy alerts

## Maintenance Notes

- API credentials should be rotated regularly
- Monitor API rate limits
- Logs can be added for debugging if needed
- Consider adding more networks as needed
- Threshold can be adjusted based on business requirements
