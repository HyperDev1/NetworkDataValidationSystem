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
    
    def get_validation_config(self) -> Dict[str, Any]:
        """Get validation/report settings."""
        return self.config.get('validation', {})
    
    def get_scheduling_config(self) -> Dict[str, Any]:
        """Get scheduling settings."""
        return self.config.get('scheduling', {})
    
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

