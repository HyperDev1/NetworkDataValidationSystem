"""
Main validation service orchestrating data fetching, validation, and notifications.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any
from src.config import Config
from src.fetchers import AdjustFetcher, ApplovinFetcher, NetworkDataFetcher
from src.validators import DataValidator
from src.notifiers import SlackNotifier


class ValidationService:
    """Main service for orchestrating network data validation."""
    
    def __init__(self, config: Config):
        """
        Initialize validation service.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.fetchers: List[NetworkDataFetcher] = []
        self.validator = None
        self.notifier = None
        
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize fetchers, validator, and notifier based on configuration."""
        # Initialize fetchers
        adjust_config = self.config.get_adjust_config()
        if adjust_config and adjust_config.get('api_token') and adjust_config.get('app_token'):
            self.fetchers.append(
                AdjustFetcher(
                    api_token=adjust_config['api_token'],
                    app_token=adjust_config['app_token']
                )
            )
        
        applovin_config = self.config.get_applovin_config()
        if applovin_config and applovin_config.get('api_key') and applovin_config.get('package_name'):
            self.fetchers.append(
                ApplovinFetcher(
                    api_key=applovin_config['api_key'],
                    package_name=applovin_config['package_name']
                )
            )
        
        # Initialize validator
        validation_config = self.config.get_validation_config()
        threshold = validation_config.get('threshold_percentage', 5.0)
        self.validator = DataValidator(threshold_percentage=threshold)
        
        # Initialize notifier
        slack_config = self.config.get_slack_config()
        if slack_config and slack_config.get('webhook_url'):
            self.notifier = SlackNotifier(
                webhook_url=slack_config['webhook_url'],
                channel=slack_config.get('channel')
            )
    
    def run_validation(self) -> Dict[str, Any]:
        """
        Run validation check for network data.
        
        Returns:
            Dictionary containing validation results
        """
        print(f"[{datetime.now()}] Starting validation check...")
        
        # Calculate date range
        validation_config = self.config.get_validation_config()
        date_range_days = validation_config.get('date_range_days', 1)
        end_date = datetime.now() - timedelta(days=1)  # Yesterday
        start_date = end_date - timedelta(days=date_range_days - 1)
        
        print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Fetch data from all networks
        network_data = []
        for fetcher in self.fetchers:
            try:
                print(f"Fetching data from {fetcher.get_network_name()}...")
                data = fetcher.fetch_data(start_date, end_date)
                network_data.append(data)
                # Ensure impressions is an integer for display
                impressions = int(data['impressions']) if isinstance(data['impressions'], (int, float)) else data['impressions']
                print(f"  Revenue: ${data['revenue']:,.2f}, Impressions: {impressions:,}")
            except Exception as e:
                print(f"  Error fetching data from {fetcher.get_network_name()}: {str(e)}")
        
        if len(network_data) < 2:
            print("Insufficient data: Need at least 2 networks to compare")
            return {
                'success': False,
                'message': 'Insufficient data to compare (need at least 2 networks)'
            }
        
        # Compare data
        print("\nComparing network data...")
        metrics = validation_config.get('metrics', ['revenue', 'impressions'])
        comparisons = self.validator.compare_multiple_networks(network_data, metrics)
        
        # Check for discrepancies
        has_discrepancy = self.validator.has_any_discrepancy(comparisons)
        
        if has_discrepancy:
            print("⚠️  Discrepancies detected!")
            for comp in comparisons:
                if comp['has_discrepancy']:
                    print(f"\n{comp['network1']} vs {comp['network2']}:")
                    for disc in comp['discrepancies']:
                        if disc['over_threshold']:
                            diff_pct = disc['difference_percentage']
                            if diff_pct == float('inf'):
                                print(f"  - {disc['metric']}: ∞% difference (baseline was 0)")
                            else:
                                print(f"  - {disc['metric']}: {diff_pct:.2f}% difference")
            
            # Send notification
            if self.notifier:
                print("\nSending Slack notification...")
                success = self.notifier.send_discrepancy_alert(comparisons)
                if success:
                    print("✅ Notification sent successfully")
                else:
                    print("❌ Failed to send notification")
        else:
            print("✅ No discrepancies detected - all networks are aligned")
        
        return {
            'success': True,
            'has_discrepancy': has_discrepancy,
            'comparisons': comparisons,
            'timestamp': datetime.now().isoformat()
        }
    
    def test_slack_integration(self) -> bool:
        """
        Test Slack integration by sending a test message.
        
        Returns:
            True if test successful, False otherwise
        """
        if not self.notifier:
            print("Slack notifier not configured")
            return False
        
        print("Sending test message to Slack...")
        success = self.notifier.send_test_message()
        
        if success:
            print("✅ Test message sent successfully")
        else:
            print("❌ Failed to send test message")
        
        return success
