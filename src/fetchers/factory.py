"""
Fetcher Factory - Centralized network fetcher initialization.

This module provides a factory pattern for creating network fetchers,
eliminating duplicate initialization code in validation_service.py.
"""
import logging
from typing import Dict, Any, Optional

from .base_fetcher import NetworkDataFetcher
from .mintegral_fetcher import MintegralFetcher
from .unity_fetcher import UnityAdsFetcher
from .admob_fetcher import AdmobFetcher
from .meta_fetcher import MetaFetcher
from .moloco_fetcher import MolocoFetcher
from .ironsource_fetcher import IronSourceFetcher
from .inmobi_fetcher import InMobiFetcher
from .bidmachine_fetcher import BidMachineFetcher
from .liftoff_fetcher import LiftoffFetcher
from .dt_exchange_fetcher import DTExchangeFetcher
from .pangle_fetcher import PangleFetcher


logger = logging.getLogger(__name__)


# Registry of network fetchers with their configuration
# Format: 'network_key': {
#     'class': FetcherClass,
#     'required_key': 'key to check if config is valid',
#     'config_mapper': function to map config dict to fetcher kwargs
# }
FETCHER_REGISTRY: Dict[str, Dict[str, Any]] = {
    'mintegral': {
        'class': MintegralFetcher,
        'required_key': 'skey',
        'config_mapper': lambda cfg: {
            'skey': cfg['skey'],
            'secret': cfg['secret'],
            'app_id': cfg.get('app_ids')
        }
    },
    'unity': {
        'class': UnityAdsFetcher,
        'required_key': 'api_key',
        'config_mapper': lambda cfg: {
            'api_key': cfg['api_key'],
            'organization_id': cfg.get('organization_id'),
            'game_ids': cfg.get('game_ids')
        }
    },
    'admob': {
        'class': AdmobFetcher,
        'required_key': 'oauth_credentials_path',
        'config_mapper': lambda cfg: {
            'publisher_id': cfg['publisher_id'],
            'app_ids': cfg.get('app_ids'),
            'oauth_credentials_path': cfg['oauth_credentials_path'],
            'token_path': cfg.get('token_path', 'credentials/admob_token.json')
        }
    },
    'meta': {
        'class': MetaFetcher,
        'required_key': 'access_token',
        'config_mapper': lambda cfg: {
            'access_token': cfg['access_token'],
            'business_id': cfg['business_id']
        }
    },
    'moloco': {
        'class': MolocoFetcher,
        'required_key': 'publisher_id',
        'config_mapper': lambda cfg: {
            'email': cfg['email'],
            'password': cfg['password'],
            'platform_id': cfg['platform_id'],
            'publisher_id': cfg['publisher_id'],
            'app_bundle_ids': cfg.get('app_bundle_ids'),
            'time_zone': cfg.get('time_zone', 'UTC'),
            'ad_unit_mapping': cfg.get('ad_unit_mapping', {})
        }
    },
    'ironsource': {
        'class': IronSourceFetcher,
        'required_key': 'secret_key',
        'config_mapper': lambda cfg: {
            'username': cfg['username'],
            'secret_key': cfg['secret_key'],
            'android_app_keys': cfg.get('android_app_keys'),
            'ios_app_keys': cfg.get('ios_app_keys')
        }
    },
    'inmobi': {
        'class': InMobiFetcher,
        'required_key': 'secret_key',
        'config_mapper': lambda cfg: {
            'account_id': cfg['account_id'],
            'secret_key': cfg['secret_key'],
            'username': cfg.get('username'),
            'app_ids': cfg.get('app_ids')
        }
    },
    'bidmachine': {
        'class': BidMachineFetcher,
        'required_key': 'username',
        'config_mapper': lambda cfg: {
            'username': cfg['username'],
            'password': cfg['password'],
            'app_bundle_ids': cfg.get('app_bundle_ids')
        }
    },
    'liftoff': {
        'class': LiftoffFetcher,
        'required_key': 'api_key',
        'config_mapper': lambda cfg: {
            'api_key': cfg['api_key'],
            'application_ids': cfg.get('application_ids')
        }
    },
    'dt_exchange': {
        'class': DTExchangeFetcher,
        'required_key': 'client_id',
        'config_mapper': lambda cfg: {
            'client_id': cfg['client_id'],
            'client_secret': cfg['client_secret'],
            'source': cfg.get('source', 'mediation'),
            'app_ids': cfg.get('app_ids')
        }
    },
    'pangle': {
        'class': PangleFetcher,
        'required_key': 'secure_key',
        'config_mapper': lambda cfg: {
            'user_id': cfg['user_id'],
            'role_id': cfg['role_id'],
            'secure_key': cfg['secure_key'],
            'time_zone': cfg.get('time_zone', 0),
            'currency': cfg.get('currency', 'usd'),
            'package_names': cfg.get('package_names')
        }
    },
}


class FetcherFactory:
    """Factory for creating network fetchers from configuration."""
    
    @staticmethod
    def create_fetcher(network_key: str, config: Dict[str, Any]) -> Optional[NetworkDataFetcher]:
        """
        Create a single network fetcher from configuration.
        
        Args:
            network_key: Network identifier (e.g., 'mintegral', 'unity')
            config: Network-specific configuration dictionary
            
        Returns:
            Initialized fetcher instance or None if disabled/failed
        """
        if network_key not in FETCHER_REGISTRY:
            logger.warning(f"Unknown network: {network_key}")
            return None
        
        registry_entry = FETCHER_REGISTRY[network_key]
        required_key = registry_entry['required_key']
        
        # Check if enabled and has required config
        if not config.get('enabled', False):
            return None
        
        if not config.get(required_key):
            logger.debug(f"{network_key} missing required key: {required_key}")
            return None
        
        try:
            fetcher_class = registry_entry['class']
            config_mapper = registry_entry['config_mapper']
            kwargs = config_mapper(config)
            
            fetcher = fetcher_class(**kwargs)
            logger.info(f"{network_key.replace('_', ' ').title()} fetcher initialized")
            return fetcher
            
        except ImportError as e:
            logger.warning(f"{network_key} fetcher skipped (import error): {e}")
        except FileNotFoundError as e:
            logger.warning(f"{network_key} fetcher skipped (file not found): {e}")
        except Exception as e:
            logger.warning(f"{network_key} fetcher skipped: {e}")
        
        return None
    
    @classmethod
    def create_all_fetchers(cls, config) -> Dict[str, NetworkDataFetcher]:
        """
        Create all enabled network fetchers from Config object.
        
        Args:
            config: Config instance with get_networks_config() method
            
        Returns:
            Dictionary mapping network keys to fetcher instances
        """
        fetchers = {}
        networks_config = config.get_networks_config()
        
        for network_key in FETCHER_REGISTRY.keys():
            network_config = networks_config.get(network_key, {})
            fetcher = cls.create_fetcher(network_key, network_config)
            
            if fetcher is not None:
                fetchers[network_key] = fetcher
        
        logger.info(f"Initialized {len(fetchers)}/{len(FETCHER_REGISTRY)} network fetchers")
        return fetchers
    
    @staticmethod
    def get_supported_networks() -> list:
        """Get list of all supported network keys."""
        return list(FETCHER_REGISTRY.keys())
