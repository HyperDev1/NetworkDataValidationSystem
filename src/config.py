"""
Configuration loader for the Network Data Validation System.
"""
import yaml
import os
from typing import Dict, Any, List


class Config:
    """Configuration manager for loading and accessing settings."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize configuration.
        
        Args:
            config_path: Path to the configuration YAML file
        """
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_path}\n"
                f"Please copy config.yaml.example to config.yaml and configure it."
            )
        
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.
        
        Args:
            key: Configuration key (supports nested keys with dots, e.g., 'slack.webhook_url')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_applovin_config(self) -> Dict[str, Any]:
        """Get Applovin API configuration."""
        return self.config.get('applovin', {})
    
    def get_slack_config(self) -> Dict[str, str]:
        """Get Slack configuration."""
        return self.config.get('slack', {})
    
    def get_slack_revenue_delta_threshold(self) -> float:
        """
        Get revenue delta threshold for Slack notifications.
        Only rows with |rev_delta| > threshold will be shown in Slack.
        
        Returns:
            Threshold percentage (default: 5.0)
        """
        slack_config = self.get_slack_config()
        return float(slack_config.get('revenue_delta_threshold', 5.0))
    
    def get_slack_min_revenue_for_alerts(self) -> float:
        """
        Get minimum revenue threshold for Slack alerts.
        Only rows with max_revenue >= this value will be checked against percentage threshold.
        This prevents alerts on low-revenue placements with high percentage differences.
        
        Returns:
            Minimum revenue in dollars (default: 25.0)
        """
        slack_config = self.get_slack_config()
        return float(slack_config.get('min_revenue_for_alerts', 25.0))
    
    def get_validation_config(self) -> Dict[str, Any]:
        """Get validation/report settings."""
        return self.config.get('validation', {})
    
    def get_scheduling_config(self) -> Dict[str, Any]:
        """Get scheduling settings."""
        return self.config.get('scheduling', {})
    
    def get_scheduling_interval_hours(self) -> int:
        """
        Get scheduling interval in hours.
        
        Returns:
            Interval in hours (default: 3)
        """
        scheduling_config = self.get_scheduling_config()
        return int(scheduling_config.get('interval_hours', 3))
    
    def get_scheduling_start_time(self) -> str:
        """
        Get scheduling start time (base time for interval calculations).
        
        Returns:
            Start time in HH:MM format (default: "00:00")
        """
        scheduling_config = self.get_scheduling_config()
        return scheduling_config.get('start_time', '00:00')
    
    def get_scheduled_times(self) -> List[str]:
        """
        Calculate all scheduled run times based on start_time and interval_hours.
        
        Returns:
            List of times in HH:MM format (e.g., ["00:00", "03:00", "06:00", ...])
        """
        interval_hours = self.get_scheduling_interval_hours()
        start_time = self.get_scheduling_start_time()
        
        # Parse start time
        start_hour, start_minute = map(int, start_time.split(':'))
        
        # Generate all scheduled times
        times = []
        current_hour = start_hour
        while True:
            times.append(f"{current_hour:02d}:{start_minute:02d}")
            current_hour = (current_hour + interval_hours) % 24
            if current_hour == start_hour:
                break
        
        return sorted(times)
    
    def get_networks_config(self) -> Dict[str, Any]:
        """Get all networks configuration."""
        return self.config.get('networks', {})
    
    def get_enabled_networks(self) -> List[str]:
        """Get list of enabled network names."""
        networks = self.get_networks_config()
        return [name for name, cfg in networks.items() if cfg.get('enabled', False)]
    
    def get_mintegral_config(self) -> Dict[str, Any]:
        """Get Mintegral API configuration."""
        return self.config.get('networks', {}).get('mintegral', {})
    
    def get_unity_config(self) -> Dict[str, Any]:
        """Get Unity Ads API configuration."""
        return self.config.get('networks', {}).get('unity', {})
    
    def get_admob_config(self) -> Dict[str, Any]:
        """Get Google AdMob API configuration."""
        return self.config.get('networks', {}).get('admob', {})
    
    def get_ironsource_config(self) -> Dict[str, Any]:
        """Get IronSource API configuration."""
        return self.config.get('networks', {}).get('ironsource', {})
    
    def get_meta_config(self) -> Dict[str, Any]:
        """Get Meta Audience Network API configuration."""
        return self.config.get('networks', {}).get('meta', {})
    
    def get_inmobi_config(self) -> Dict[str, Any]:
        """Get InMobi API configuration."""
        return self.config.get('networks', {}).get('inmobi', {})

    def get_moloco_config(self) -> Dict[str, Any]:
        """Get Moloco API configuration."""
        return self.config.get('networks', {}).get('moloco', {})

    def get_bidmachine_config(self) -> Dict[str, Any]:
        """Get BidMachine SSP API configuration."""
        return self.config.get('networks', {}).get('bidmachine', {})

    def get_liftoff_config(self) -> Dict[str, Any]:
        """Get Liftoff (Vungle) API configuration."""
        return self.config.get('networks', {}).get('liftoff', {})

    def get_dt_exchange_config(self) -> Dict[str, Any]:
        """Get DT Exchange (Digital Turbine) API configuration."""
        return self.config.get('networks', {}).get('dt_exchange', {})

    def get_pangle_config(self) -> Dict[str, Any]:
        """Get Pangle API configuration."""
        return self.config.get('networks', {}).get('pangle', {})

    def get_gcp_config(self) -> Dict[str, Any]:
        """Get Google Cloud Platform configuration for GCS/BigQuery export."""
        return self.config.get('gcp', {})

