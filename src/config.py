"""
Configuration loader for the Network Data Validation System.
"""
import logging
import os
import yaml
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Mapping of environment variable names to their nested config dict paths.
# Env var takes priority over config.yaml value (12-factor app approach).
# Only credential/secret fields are listed — structural fields (enabled, app_ids, etc.)
# must still be set in config.yaml or accepted as absent.
_ENV_VAR_MAP: List[Tuple[str, List[str]]] = [
    # AppLovin (top-level in YAML, not under 'networks')
    ('APPLOVIN_API_KEY',             ['applovin', 'api_key']),
    ('APPLOVIN_PACKAGE_NAME',        ['applovin', 'package_name']),
    # Mintegral
    ('MINTEGRAL_SKEY',               ['networks', 'mintegral', 'skey']),
    ('MINTEGRAL_SECRET',             ['networks', 'mintegral', 'secret']),
    # Unity Ads
    ('UNITY_ADS_API_KEY',            ['networks', 'unity', 'api_key']),
    ('UNITY_ADS_ORGANIZATION_ID',    ['networks', 'unity', 'organization_id']),
    # AdMob
    ('ADMOB_PUBLISHER_ID',           ['networks', 'admob', 'publisher_id']),
    ('ADMOB_OAUTH_CREDENTIALS_PATH', ['networks', 'admob', 'oauth_credentials_path']),
    ('ADMOB_TOKEN_JSON',             ['networks', 'admob', 'token_json']),
    # Meta
    ('META_ACCESS_TOKEN',            ['networks', 'meta', 'access_token']),
    ('META_BUSINESS_ID',             ['networks', 'meta', 'business_id']),
    # Moloco
    ('MOLOCO_EMAIL',                 ['networks', 'moloco', 'email']),
    ('MOLOCO_PASSWORD',              ['networks', 'moloco', 'password']),
    ('MOLOCO_PLATFORM_ID',           ['networks', 'moloco', 'platform_id']),
    # BidMachine
    ('BIDMACHINE_USERNAME',          ['networks', 'bidmachine', 'username']),
    ('BIDMACHINE_PASSWORD',          ['networks', 'bidmachine', 'password']),
    # Liftoff
    ('LIFTOFF_API_KEY',              ['networks', 'liftoff', 'api_key']),
    # DT Exchange
    ('DT_EXCHANGE_CLIENT_ID',        ['networks', 'dt_exchange', 'client_id']),
    ('DT_EXCHANGE_CLIENT_SECRET',    ['networks', 'dt_exchange', 'client_secret']),
    # Pangle
    ('PANGLE_USER_ID',               ['networks', 'pangle', 'user_id']),
    ('PANGLE_ROLE_ID',               ['networks', 'pangle', 'role_id']),
    ('PANGLE_SECURE_KEY',            ['networks', 'pangle', 'secure_key']),
    # IronSource
    ('IRONSOURCE_USERNAME',          ['networks', 'ironsource', 'username']),
    ('IRONSOURCE_SECRET_KEY',        ['networks', 'ironsource', 'secret_key']),
    # InMobi
    ('INMOBI_ACCOUNT_ID',            ['networks', 'inmobi', 'account_id']),
    ('INMOBI_SECRET_KEY',            ['networks', 'inmobi', 'secret_key']),
    ('INMOBI_USERNAME',              ['networks', 'inmobi', 'username']),
    # Slack
    ('SLACK_WEBHOOK_URL',            ['slack', 'webhook_url']),
    # GCP
    ('GCP_BUCKET_NAME',              ['gcp', 'bucket_name']),
    ('GCP_PROJECT_ID',               ['gcp', 'project_id']),
]


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
        """Load configuration from YAML file and merge env var overrides.

        If config.yaml is absent (Cloud Run), starts from an empty dict and
        populates entirely from environment variables. If config.yaml is present
        (local dev), env vars take priority over YAML values.

        Returns:
            Merged configuration dict ready for all callers including
            get_networks_config() used by FetcherFactory.
        """
        if not os.path.exists(self.config_path) or os.path.isdir(self.config_path):
            logger.warning(
                f"Config file not found at {self.config_path} — relying on environment variables"
            )
            config: Dict[str, Any] = {}
        else:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f) or {}

        return self._merge_env_vars(config)

    def _merge_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge environment variable values into config dict (env vars take priority).

        Iterates _ENV_VAR_MAP and for each env var that is set, writes its value
        into the nested config dict at the mapped path. This ensures that callers
        like FetcherFactory which index into get_networks_config() directly receive
        env var values even when config.yaml is absent.

        Also sets 'enabled: True' on any network sub-dict that receives at least one
        env var value and does not already have an 'enabled' key — this allows
        Cloud Run deployments that omit config.yaml to activate networks solely via
        env vars without requiring a separate 'enabled' flag.

        Args:
            config: YAML-loaded dict (may be empty if config.yaml absent).

        Returns:
            config dict with env var values merged in.
        """
        for env_var, path in _ENV_VAR_MAP:
            value = os.environ.get(env_var)
            if value is None:
                continue

            # Walk/create nested dicts down to the parent of the leaf
            node = config
            for key in path[:-1]:
                if key not in node or not isinstance(node[key], dict):
                    node[key] = {}
                node = node[key]

            # Write the env var value at the leaf key (overrides YAML if present)
            node[path[-1]] = value
            logger.debug(f"Config: {env_var} → {'.'.join(path)}")

            # For network sub-dicts (path[0] == 'networks'), auto-enable the network
            # if 'enabled' is not already explicitly set.
            if path[0] == 'networks' and len(path) >= 2:
                network_node = config['networks'][path[1]]
                if 'enabled' not in network_node:
                    network_node['enabled'] = True

        return config

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.

        Checks environment variable first (NETWORK_FIELD naming: remove 'networks.'
        prefix, replace dots with underscores, uppercase), then falls back to the
        merged config dict (which already reflects env var values from _merge_env_vars).

        Args:
            key: Configuration key (supports nested keys with dots, e.g., 'slack.webhook_url')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        # Env var check: remove 'networks.' prefix, replace dots with _, uppercase
        env_key = key.replace('networks.', '', 1).replace('.', '_').upper()
        env_value = os.environ.get(env_key)
        if env_value is not None:
            return env_value

        # Fall back to merged config dict (already has env vars merged in)
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
        """Get all networks configuration.

        Returns the merged config dict's 'networks' sub-dict. Because _merge_env_vars()
        has already populated env var values into self.config, this dict contains
        env var values when config.yaml is absent (Cloud Run) and YAML+env var merged
        values when config.yaml is present (local dev). FetcherFactory uses this
        method — all 12 network fetchers receive credential values from env vars.
        """
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
