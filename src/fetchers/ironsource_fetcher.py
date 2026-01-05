"""
IronSource Monetization Reporting API data fetcher implementation.
Uses IronSource Reporting API V5 for fetching monetization data.
API Docs: https://developers.is.com/ironsource-mobile/air/monetization-reporting-api
"""
import base64
import requests
from datetime import datetime
from typing import Dict, Any, Optional, List
from .base_fetcher import NetworkDataFetcher


class IronSourceFetcher(NetworkDataFetcher):
    """Fetcher for IronSource monetization data using Reporting API V5."""
    
    # IronSource API endpoints
    BASE_URL = "https://platform.ironsrc.com"
    REPORT_ENDPOINT = "/partners/publisher/mediation/applications/v5/stats"
    
    # Ad type mapping - IronSource adUnits to our standard categories
    # Note: Offerwall is excluded as per requirements
    AD_TYPE_MAP = {
        'Rewarded Video': 'rewarded',
        'rewardedVideo': 'rewarded',
        'REWARDED_VIDEO': 'rewarded',
        'Interstitial': 'interstitial',
        'interstitial': 'interstitial',
        'INTERSTITIAL': 'interstitial',
        'Banner': 'banner',
        'banner': 'banner',
        'BANNER': 'banner',
    }
    
    # Supported ad units filter (excluding Offerwall)
    SUPPORTED_AD_UNITS = "rewardedVideo,interstitial,banner"
    
    def __init__(
        self,
        username: str,
        secret_key: str,
        android_app_keys: Optional[str] = None,
        ios_app_keys: Optional[str] = None,
    ):
        """
        Initialize IronSource fetcher.
        
        Args:
            username: IronSource login email
            secret_key: IronSource Secret Key (from My Account → Reporting API)
            android_app_keys: Comma-separated Android app keys
            ios_app_keys: Comma-separated iOS app keys
        """
        self.username = username
        self.secret_key = secret_key
        self.android_app_keys = [k.strip() for k in android_app_keys.split(',') if k.strip()] if android_app_keys else []
        self.ios_app_keys = [k.strip() for k in ios_app_keys.split(',') if k.strip()] if ios_app_keys else []
        
    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Generate Basic Auth header for IronSource API.
        
        Returns:
            Dictionary with Authorization header
        """
        credentials = f"{self.username}:{self.secret_key}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        return {
            'Authorization': f'Basic {encoded_credentials}',
            'Accept': 'application/json',
        }
    
    def _create_empty_platform_data(self) -> Dict[str, Any]:
        """Create empty platform data structure."""
        return {
            'revenue': 0.0,
            'impressions': 0,
            'ecpm': 0.0,
            'requests': 0,
            'fills': 0,
            'clicks': 0,
            'ad_data': {
                'banner': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0, 'requests': 0, 'fills': 0, 'clicks': 0},
                'interstitial': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0, 'requests': 0, 'fills': 0, 'clicks': 0},
                'rewarded': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0, 'requests': 0, 'fills': 0, 'clicks': 0},
            }
        }
    
    def _fetch_platform_data(
        self,
        start_date: str,
        end_date: str,
        app_keys: List[str],
        platform: str
    ) -> Dict[str, Any]:
        """
        Fetch data for a specific platform's app keys.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            app_keys: List of app keys for this platform
            platform: Platform name ('android' or 'ios')
            
        Returns:
            Platform data dictionary
        """
        platform_data = self._create_empty_platform_data()
        
        if not app_keys:
            return platform_data
        
        headers = self._get_auth_headers()
        
        # Build query parameters
        # Request data for all app keys at once (comma-separated)
        params = {
            'startDate': start_date,
            'endDate': end_date,
            'appKey': ','.join(app_keys),
            'adUnits': self.SUPPORTED_AD_UNITS,
            'metrics': 'revenue,impressions,eCPM,clicks,appRequests,appFills',
            'breakdown': 'adUnits,date',
        }
        
        url = f"{self.BASE_URL}{self.REPORT_ENDPOINT}"
        
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=60
        )
        
        if response.status_code == 401:
            error_detail = ""
            try:
                error_detail = f" Response: {response.text[:200]}"
            except:
                pass
            raise Exception(
                f"IronSource authentication failed (401).{error_detail} "
                "Please check your username (email) and secret_key in config.yaml"
            )
        
        if response.status_code != 200:
            error_msg = f"IronSource API error: {response.status_code}"
            try:
                error_data = response.json()
                error_msg += f" - {error_data}"
            except:
                error_msg += f" - {response.text[:500]}"
            raise Exception(error_msg)
        
        # Parse response - IronSource returns JSON array at root level
        try:
            data = response.json()
        except Exception as e:
            raise Exception(f"Failed to parse IronSource response: {e}")
        
        # Response format:
        # [
        #   {
        #     "adUnits": "Rewarded Video",
        #     "date": "2018-08-01",
        #     "data": [
        #       { "revenue": 71188.8, "impressions": 13321624, "eCPM": 5.34, "clicks": 0 }
        #     ]
        #   }
        # ]
        
        if not isinstance(data, list):
            # Might be an error object
            if isinstance(data, dict) and ('error' in data or 'message' in data):
                raise Exception(f"IronSource API error: {data}")
            return platform_data
        
        for item in data:
            if not isinstance(item, dict):
                continue
            
            ad_units_raw = item.get('adUnits', '')
            ad_type = self.AD_TYPE_MAP.get(ad_units_raw, None)
            
            # Skip unsupported ad types (e.g., Offerwall)
            if ad_type is None:
                continue
            
            # Extract metrics from nested 'data' array
            metrics_list = item.get('data', [])
            
            for metrics in metrics_list:
                if not isinstance(metrics, dict):
                    continue
                
                rev = float(metrics.get('revenue', 0) or 0)
                imps = int(metrics.get('impressions', 0) or 0)
                clks = int(metrics.get('clicks', 0) or 0)
                reqs = int(metrics.get('appRequests', 0) or 0)
                fls = int(metrics.get('appFills', 0) or 0)
                
                # Aggregate platform totals
                platform_data['revenue'] += rev
                platform_data['impressions'] += imps
                platform_data['clicks'] += clks
                platform_data['requests'] += reqs
                platform_data['fills'] += fls
                
                # Aggregate by ad type
                platform_data['ad_data'][ad_type]['revenue'] += rev
                platform_data['ad_data'][ad_type]['impressions'] += imps
                platform_data['ad_data'][ad_type]['clicks'] += clks
                platform_data['ad_data'][ad_type]['requests'] += reqs
                platform_data['ad_data'][ad_type]['fills'] += fls
        
        # Calculate eCPMs
        if platform_data['impressions'] > 0:
            platform_data['ecpm'] = (platform_data['revenue'] / platform_data['impressions']) * 1000
        
        for ad_type in ['banner', 'interstitial', 'rewarded']:
            ad_data = platform_data['ad_data'][ad_type]
            if ad_data['impressions'] > 0:
                ad_data['ecpm'] = (ad_data['revenue'] / ad_data['impressions']) * 1000
        
        return platform_data
    
    def fetch_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Fetch revenue and impression data for the given date range.
        
        Args:
            start_date: Start date for data fetch
            end_date: End date for data fetch
            
        Returns:
            Dictionary containing revenue and impressions data
        """
        # Format dates as YYYY-MM-DD
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        # Initialize result structure
        result = {
            'revenue': 0.0,
            'impressions': 0,
            'ecpm': 0.0,
            'requests': 0,
            'fills': 0,
            'clicks': 0,
            'network': self.get_network_name(),
            'date_range': {'start': start_str, 'end': end_str},
            'platform_data': {
                'android': self._create_empty_platform_data(),
                'ios': self._create_empty_platform_data(),
            }
        }
        
        # Fetch data for Android apps
        if self.android_app_keys:
            android_data = self._fetch_platform_data(
                start_str, end_str, self.android_app_keys, 'android'
            )
            result['platform_data']['android'] = android_data
            
            # Add to totals
            result['revenue'] += android_data['revenue']
            result['impressions'] += android_data['impressions']
            result['clicks'] += android_data['clicks']
            result['requests'] += android_data['requests']
            result['fills'] += android_data['fills']
        
        # Fetch data for iOS apps
        if self.ios_app_keys:
            ios_data = self._fetch_platform_data(
                start_str, end_str, self.ios_app_keys, 'ios'
            )
            result['platform_data']['ios'] = ios_data
            
            # Add to totals
            result['revenue'] += ios_data['revenue']
            result['impressions'] += ios_data['impressions']
            result['clicks'] += ios_data['clicks']
            result['requests'] += ios_data['requests']
            result['fills'] += ios_data['fills']
        
        # Calculate overall eCPM
        if result['impressions'] > 0:
            result['ecpm'] = (result['revenue'] / result['impressions']) * 1000
        
        return result
    
    def get_network_name(self) -> str:
        """Return the name of the network."""
        return "IronSource"
