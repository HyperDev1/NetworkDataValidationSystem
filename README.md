# Network Data Validation System

A system for validating and comparing revenue and impression data across multiple ad networks (Adjust, Applovin Max, etc.) with automated Slack notifications for discrepancies.

## 🎯 Features

- **Multi-Network Support**: Fetch data from Adjust, Applovin Max, and easily extensible to other networks
- **Automated Comparison**: Compare revenue and impression metrics across networks
- **Configurable Thresholds**: Set custom threshold percentages for acceptable differences
- **Slack Notifications**: Automatic alerts when discrepancies exceed thresholds
- **Scheduled Checks**: Periodic validation with configurable intervals
- **Easy Configuration**: YAML-based configuration for all settings

## 📋 Requirements

- Python 3.7+
- Valid API credentials for:
  - Adjust API
  - Applovin Max API
- Slack Webhook URL for notifications

## 🚀 Installation

1. Clone the repository:
```bash
git clone https://github.com/HyperDev1/NetworkDataValidationSystem.git
cd NetworkDataValidationSystem
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create configuration file:
```bash
cp config.yaml.example config.yaml
```

4. Edit `config.yaml` with your credentials and settings:
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

## 💻 Usage

### Run with Scheduling (Continuous Mode)

Run the system continuously with periodic checks:
```bash
python main.py
```

This will:
- Run an immediate validation check
- Schedule checks every N hours (configured in `config.yaml`)
- Continue running until stopped with Ctrl+C

### Run Once

Execute a single validation check and exit:
```bash
python main.py --once
```

### Test Slack Integration

Send a test message to Slack to verify configuration:
```bash
python main.py --test-slack
```

### Help

Display usage information:
```bash
python main.py --help
```

## 📊 How It Works

1. **Data Fetching**: The system fetches revenue and impression data from configured networks for the specified date range
2. **Comparison**: Compares metrics between networks (using the first network as baseline)
3. **Validation**: Calculates percentage differences and checks against threshold
4. **Notification**: If discrepancies exceed the threshold, sends a detailed alert to Slack
5. **Scheduling**: Repeats the process at configured intervals

## 🔧 Configuration Options

### Network Configuration

- **Adjust**: Requires `api_token` and `app_token`
- **Applovin Max**: Requires `api_key` and `package_name`
- **Mintegral**: Requires `skey`, `secret`, and optional `app_ids`
- **Unity Ads**: Requires `api_key`, `organization_id`, and optional `game_ids`
- **Google AdMob**: Requires `service_account_json_path` and `publisher_id` (see AdMob Setup below)

### AdMob Setup

1. **Enable AdMob API in Google Cloud Console:**
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Select or create a project
   - Navigate to APIs & Services → Library
   - Search for "AdMob API" and enable it

2. **Create Service Account:**
   - Go to IAM & Admin → Service Accounts
   - Click "Create Service Account"
   - Enter a name (e.g., "admob-reporter")
   - Click "Create and Continue"
   - Skip role assignment (not needed for AdMob)
   - Click "Done"
   - Click on the created service account
   - Go to "Keys" tab → Add Key → Create new key → JSON
   - Download the JSON file to `credentials/admob-service-account.json`

3. **Grant AdMob Access:**
   - Go to [AdMob Console](https://apps.admob.com)
   - Navigate to Settings → Access & Authorization → Users
   - Click "Invite new user"
   - Enter the Service Account email (from JSON file: `client_email`)
   - Select appropriate role and send invitation

4. **Configure in config.yaml:**
   ```yaml
   networks:
     admob:
       enabled: true
       service_account_json_path: "credentials/admob-service-account.json"
       publisher_id: "pub-XXXXXXXXXXXXXXXX"
       app_ids: ""  # Optional: comma-separated AdMob app IDs
   ```

### Validation Settings

- `threshold_percentage`: Maximum allowed difference (default: 5%)
- `metrics`: List of metrics to compare (revenue, impressions)
- `date_range_days`: Number of days to fetch data for (default: 1)

### Scheduling Settings

- `interval_hours`: Hours between validation checks (default: 6)
- `enabled`: Enable/disable scheduling (default: true)

### Slack Settings

- `webhook_url`: Slack Incoming Webhook URL (required)
- `channel`: Slack channel to post to (optional, overrides webhook default)

## 📝 Example Output

### Console Output
```
Network Data Validation System
============================================================
✅ Configuration loaded successfully

🔄 Scheduling validation checks every 6 hour(s)
Press Ctrl+C to stop

============================================================
[2025-12-26 19:00:00] Starting validation check...
Date range: 2025-12-25 to 2025-12-25
Fetching data from Adjust...
  Revenue: $1,234.56, Impressions: 123,456
Fetching data from Applovin Max...
  Revenue: $1,100.00, Impressions: 115,000

Comparing network data...
⚠️  Discrepancies detected!

Adjust vs Applovin Max:
  - revenue: 10.92% difference
  - impressions: 6.85% difference

Sending Slack notification...
✅ Notification sent successfully
============================================================
```

### Slack Notification

The system sends formatted Slack messages with:
- Alert header with warning emoji
- Date range and timestamp
- Detailed comparison for each metric
- Formatted values (currency for revenue, thousands separator for impressions)
- Percentage differences highlighted

## 🔌 Adding New Networks

To add support for a new network:

1. Create a new fetcher in `src/fetchers/`:
```python
from .base_fetcher import NetworkDataFetcher

class NewNetworkFetcher(NetworkDataFetcher):
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def fetch_data(self, start_date, end_date):
        # Implement API call
        return {
            'revenue': 0.0,
            'impressions': 0,
            'network': self.get_network_name(),
            'date_range': {...}
        }
    
    def get_network_name(self):
        return "New Network"
```

2. Add configuration in `config.yaml`:
```yaml
new_network:
  api_key: "YOUR_API_KEY"
```

3. Register in `src/validation_service.py`:
```python
from src.fetchers import NewNetworkFetcher

# In _initialize_components method:
new_network_config = self.config.get('new_network', {})
if new_network_config and new_network_config.get('api_key'):
    self.fetchers.append(
        NewNetworkFetcher(api_key=new_network_config['api_key'])
    )
```

## 🛠️ Development

### Project Structure
```
NetworkDataValidationSystem/
├── main.py                 # Main entry point
├── config.yaml            # Configuration file (create from example)
├── config.yaml.example    # Example configuration
├── requirements.txt       # Python dependencies
├── src/
│   ├── config.py         # Configuration loader
│   ├── validation_service.py  # Main validation orchestrator
│   ├── fetchers/         # Network data fetchers
│   │   ├── base_fetcher.py
│   │   ├── adjust_fetcher.py
│   │   └── applovin_fetcher.py
│   ├── validators/       # Data validation logic
│   │   └── data_validator.py
│   └── notifiers/        # Notification systems
│       └── slack_notifier.py
└── README.md
```

## 🔒 Security Notes

- Never commit `config.yaml` with real credentials (it's in `.gitignore`)
- Use environment variables for sensitive data in production
- Rotate API keys regularly
- Limit Slack webhook permissions to specific channels

## 📄 License

MIT License

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## ❓ Troubleshooting

### "Configuration file not found"
- Make sure you've created `config.yaml` from `config.yaml.example`

### "Failed to fetch data from [Network]"
- Verify your API credentials are correct
- Check network connectivity
- Ensure API endpoints are accessible
- Review API rate limits

### "Failed to send Slack notification"
- Verify your webhook URL is correct
- Check if the Slack app has necessary permissions
- Test with `--test-slack` flag

### "Insufficient data to compare"
- Ensure at least 2 networks are configured with valid credentials
- Check if API calls are returning data