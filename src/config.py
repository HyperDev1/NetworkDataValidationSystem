"""
Configuration loader for the Network Data Validation System.
"""
import yaml
import os
from typing import Dict, Any


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
    
    def get_adjust_config(self) -> Dict[str, str]:
        """Get Adjust API configuration."""
        return self.config.get('adjust', {})
    
    def get_applovin_config(self) -> Dict[str, str]:
        """Get Applovin API configuration."""
        return self.config.get('applovin', {})
    
    def get_slack_config(self) -> Dict[str, str]:
        """Get Slack configuration."""
        return self.config.get('slack', {})
    
    def get_validation_config(self) -> Dict[str, Any]:
        """Get validation settings."""
        return self.config.get('validation', {})
    
    def get_scheduling_config(self) -> Dict[str, Any]:
        """Get scheduling settings."""
        return self.config.get('scheduling', {})
