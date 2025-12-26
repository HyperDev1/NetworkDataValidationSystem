"""
Applovin Max data fetcher implementation.
Fetches both total data and per-network breakdown for mediation comparison.
"""
import requests
from datetime import datetime
from typing import Dict, Any, List
from .base_fetcher import NetworkDataFetcher


class ApplovinFetcher(NetworkDataFetcher):
    """Fetcher for Applovin Max network data with mediation network breakdown."""
    
    # Ad format mapping
    AD_FORMATS = ['BANNER', 'INTER', 'REWARDED']
    AD_FORMAT_NAMES = {
        'BANNER': 'Banner',
        'INTER': 'Interstitial', 
        'REWARDED': 'Rewarded'
    }
    
    # Network name mapping (Applovin network names to our standard names)
    NETWORK_NAME_MAP = {
        'APPLOVIN': 'AppLovin',
        'ADMOB': 'AdMob',
        'FACEBOOK': 'Meta',
        'META_AUDIENCE_NETWORK': 'Meta',
        'MINTEGRAL': 'Mintegral',
        'UNITY': 'Unity Ads',
        'UNITY_ADS': 'Unity Ads',
        'IRONSOURCE': 'IronSource',
        'VUNGLE': 'Vungle',
        'CHARTBOOST': 'Chartboost',
        'INMOBI': 'InMobi',
        'PANGLE': 'Pangle',
        'BYTEDANCE': 'Pangle',
        'ADJUST': 'Adjust',
        'APPSFLYER': 'AppsFlyer',
    }
    
    def __init__(self, api_key: str, package_name: str):
        """
        Initialize Applovin fetcher.
        
        Args:
            api_key: Applovin API key
            package_name: App package name
        """
        self.api_key = api_key
        self.package_name = package_name
        self.base_url = "https://r.applovin.com/maxReport"
    
    def _detect_platform(self, row: Dict[str, Any]) -> str:
        """Detect platform (android/ios) from API row."""
        platform_val = str(row.get('os', row.get('platform', row.get('os_name', '')))).lower()
        if 'android' in platform_val:
            return 'android'
        if 'ios' in platform_val or 'iphone' in platform_val or 'ipad' in platform_val:
            return 'ios'
        return 'android'
    
    def _normalize_network_name(self, network: str) -> str:
        """Normalize network name to standard format."""
        if not network:
            return 'Unknown'
        
        # Remove common suffixes
        network_clean = network.replace('_Bidding', '').replace('_Network', '').replace('_Exchange', '')
        network_upper = network_clean.upper().strip()
        
        # Direct mapping
        if network_upper in self.NETWORK_NAME_MAP:
            return self.NETWORK_NAME_MAP[network_upper]
        
        # Return cleaned title case
        return network_clean.replace('_', ' ').title()
    
    def _detect_ad_type(self, row: Dict[str, Any]) -> str:
        """Detect ad type from row data."""
        ad_format = (row.get('ad_format') or row.get('format') or row.get('format_name') or '')
        if isinstance(ad_format, str):
            ad_format_up = ad_format.upper()
        else:
            ad_format_up = str(ad_format).upper()
        
        if 'BANNER' in ad_format_up:
            return 'banner'
        elif 'INTER' in ad_format_up or 'INTERSTITIAL' in ad_format_up:
            return 'interstitial'
        elif 'REWARD' in ad_format_up or 'REWARDED' in ad_format_up:
            return 'rewarded'
        else:
            inferred = str(row.get('placement_type', '')).lower()
            if 'banner' in inferred:
                return 'banner'
            elif 'reward' in inferred:
                return 'rewarded'
            return 'interstitial'
    
    def _init_platform_data(self) -> Dict[str, Any]:
        """Initialize empty platform data structure."""
        ad_types = ['banner', 'interstitial', 'rewarded']
        return {
            'android': {
                'ad_data': {k: {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0} for k in ad_types},
                'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0
            },
            'ios': {
                'ad_data': {k: {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0} for k in ad_types},
                'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0
            }
        }
    
    def _calculate_ecpm(self, data: Dict[str, Any]):
        """Calculate eCPM values in place."""
        # Ad data eCPM
        if 'ad_data' in data:
            for key in data['ad_data']:
                imp = data['ad_data'][key]['impressions']
                rev = data['ad_data'][key]['revenue']
                data['ad_data'][key]['ecpm'] = round((rev / imp * 1000) if imp > 0 else 0.0, 2)
                data['ad_data'][key]['revenue'] = round(rev, 2)
        
        # Platform data eCPM
        if 'platform_data' in data:
            for plat in data['platform_data']:
                plat_data = data['platform_data'][plat]
                plat_imp = plat_data['impressions']
                plat_rev = plat_data['revenue']
                plat_data['ecpm'] = round((plat_rev / plat_imp * 1000) if plat_imp > 0 else 0.0, 2)
                plat_data['revenue'] = round(plat_rev, 2)
                
                for key in plat_data.get('ad_data', {}):
                    aimp = plat_data['ad_data'][key]['impressions']
                    arev = plat_data['ad_data'][key]['revenue']
                    plat_data['ad_data'][key]['ecpm'] = round((arev / aimp * 1000) if aimp > 0 else 0.0, 2)
                    plat_data['ad_data'][key]['revenue'] = round(arev, 2)
    
    def fetch_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Fetch data from Applovin Max API with network breakdown.
        
        Returns:
            Dictionary containing total data + network_breakdown for each mediation network
        """
        # Try to fetch with network column for mediation breakdown
        column_variants = [
            "day,package_name,network,ad_format,estimated_revenue,impressions,platform",
            "day,package_name,network,ad_format,estimated_revenue,impressions,os",
            "day,package_name,ad_format,estimated_revenue,impressions,platform",
            "day,package_name,ad_format,estimated_revenue,impressions,os",
            "day,package_name,estimated_revenue,impressions,platform",
            "day,package_name,estimated_revenue,impressions,os",
        ]

        data = None
        has_network_data = False
        last_exception = None
        
        for cols in column_variants:
            params = {
                "api_key": self.api_key,
                "start": start_date.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d"),
                "columns": cols,
                "format": "json",
                "filter_package_name": self.package_name
            }

            try:
                response = requests.get(self.base_url, params=params, timeout=30)
                if response.status_code >= 400 and response.status_code < 500:
                    last_exception = Exception(f"Applovin returned {response.status_code}: {response.text}")
                    continue
                response.raise_for_status()
                data = response.json()
                if not data or (not data.get('results') and not data.get('data') and not data.get('rows')):
                    last_exception = Exception(f"Applovin returned unexpected payload")
                    data = None
                    continue
                # Check if we got network data
                has_network_data = 'network' in cols
                break
            except requests.exceptions.RequestException as e:
                last_exception = e
                data = None
                continue

        if data is None:
            raise Exception(f"Failed to fetch data from Applovin Max: {str(last_exception)}")

        # Initialize structures
        ad_data = {
            'banner': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0},
            'interstitial': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0},
            'rewarded': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0}
        }
        platform_data = self._init_platform_data()
        network_breakdown = {}  # Per-network data as seen in Applovin
        
        total_revenue = 0.0
        total_impressions = 0

        rows = data.get('results') or data.get('data') or data.get('rows') or []
        
        for row in rows:
            try:
                revenue = float(row.get('estimated_revenue', row.get('revenue', 0)))
            except (TypeError, ValueError):
                revenue = 0.0
            try:
                impressions = int(row.get('impressions', row.get('impression', 0)))
            except (TypeError, ValueError):
                impressions = 0

            platform = self._detect_platform(row)
            ad_type = self._detect_ad_type(row)
            network = self._normalize_network_name(row.get('network', ''))

            # Accumulate totals
            total_revenue += revenue
            total_impressions += impressions
            
            # Accumulate by ad type
            ad_data[ad_type]['revenue'] += revenue
            ad_data[ad_type]['impressions'] += impressions
            
            # Accumulate by platform
            platform_data[platform]['ad_data'][ad_type]['revenue'] += revenue
            platform_data[platform]['ad_data'][ad_type]['impressions'] += impressions
            platform_data[platform]['revenue'] += revenue
            platform_data[platform]['impressions'] += impressions
            
            # Accumulate by network (for mediation comparison)
            if has_network_data and network and network != 'Unknown':
                if network not in network_breakdown:
                    network_breakdown[network] = {
                        'revenue': 0.0,
                        'impressions': 0,
                        'ecpm': 0.0,
                        'ad_data': {k: {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0} for k in ad_data},
                        'platform_data': self._init_platform_data()
                    }
                
                nb = network_breakdown[network]
                nb['revenue'] += revenue
                nb['impressions'] += impressions
                nb['ad_data'][ad_type]['revenue'] += revenue
                nb['ad_data'][ad_type]['impressions'] += impressions
                nb['platform_data'][platform]['revenue'] += revenue
                nb['platform_data'][platform]['impressions'] += impressions
                nb['platform_data'][platform]['ad_data'][ad_type]['revenue'] += revenue
                nb['platform_data'][platform]['ad_data'][ad_type]['impressions'] += impressions

        # Calculate eCPMs
        result = {
            'revenue': round(total_revenue, 2),
            'impressions': total_impressions,
            'ecpm': round((total_revenue / total_impressions * 1000) if total_impressions > 0 else 0.0, 2),
            'ad_data': ad_data,
            'platform_data': platform_data,
            'network': self.get_network_name(),
            'date_range': {
                'start': start_date.strftime("%Y-%m-%d"),
                'end': end_date.strftime("%Y-%m-%d")
            },
            'network_breakdown': network_breakdown
        }
        
        self._calculate_ecpm(result)
        
        # Calculate eCPM for each network in breakdown
        for net_name, net_data in network_breakdown.items():
            net_data['ecpm'] = round((net_data['revenue'] / net_data['impressions'] * 1000) if net_data['impressions'] > 0 else 0.0, 2)
            net_data['revenue'] = round(net_data['revenue'], 2)
            self._calculate_ecpm(net_data)
        
        return result

    def get_network_name(self) -> str:
        """Return the network name."""
        return "Applovin Max"

