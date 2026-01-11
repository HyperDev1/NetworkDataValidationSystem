"""
IronSource Monetization Reporting API data fetcher implementation.
Async version using aiohttp with retry support.
Uses IronSource Reporting API V5 for fetching monetization data.
API Docs: https://developers.is.com/ironsource-mobile/air/monetization-reporting-api
"""
import base64
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from .base_fetcher import NetworkDataFetcher, FetchResult
from ..enums import Platform, AdType, NetworkName


logger = logging.getLogger(__name__)


class IronSourceFetcher(NetworkDataFetcher):
    """Fetcher for IronSource monetization data using Reporting API V5."""
    
    # IronSource API endpoints
    BASE_URL = "https://platform.ironsrc.com"
    REPORT_ENDPOINT = "/partners/publisher/mediation/applications/v5/stats"
    
    # Ad type mapping - IronSource adUnits to AdType enum
    AD_TYPE_MAP = {
        'Rewarded Video': AdType.REWARDED,
        'rewardedVideo': AdType.REWARDED,
        'REWARDED_VIDEO': AdType.REWARDED,
        'Interstitial': AdType.INTERSTITIAL,
        'interstitial': AdType.INTERSTITIAL,
        'INTERSTITIAL': AdType.INTERSTITIAL,
        'Banner': AdType.BANNER,
        'banner': AdType.BANNER,
        'BANNER': AdType.BANNER,
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
        super().__init__()
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
    
    def _create_extended_platform_data(self) -> Dict[str, Any]:
        """Create empty platform data structure with extended metrics."""
        base = self._init_platform_data()
        for platform in base:
            base[platform]['requests'] = 0
            base[platform]['fills'] = 0
            base[platform]['clicks'] = 0
            for ad_type in base[platform]['ad_data']:
                base[platform]['ad_data'][ad_type]['requests'] = 0
                base[platform]['ad_data'][ad_type]['fills'] = 0
                base[platform]['ad_data'][ad_type]['clicks'] = 0
        return base
    
    async def _fetch_platform_data(
        self,
        start_date: str,
        end_date: str,
        app_keys: List[str],
        platform: Platform
    ) -> Dict[str, Any]:
        """
        Fetch data for a specific platform's app keys.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            app_keys: List of app keys for this platform
            platform: Platform enum
            
        Returns:
            Platform data dictionary
        """
        platform_data = {
            'revenue': 0.0,
            'impressions': 0,
            'ecpm': 0.0,
            'requests': 0,
            'fills': 0,
            'clicks': 0,
            'ad_data': self._init_ad_data()
        }
        
        # Add extended fields to ad_data
        for ad_type in platform_data['ad_data']:
            platform_data['ad_data'][ad_type]['requests'] = 0
            platform_data['ad_data'][ad_type]['fills'] = 0
            platform_data['ad_data'][ad_type]['clicks'] = 0
        
        if not app_keys:
            return platform_data
        
        headers = self._get_auth_headers()
        
        # Build query parameters
        params = {
            'startDate': start_date,
            'endDate': end_date,
            'appKey': ','.join(app_keys),
            'adUnits': self.SUPPORTED_AD_UNITS,
            'metrics': 'revenue,impressions,eCPM,clicks,appRequests,appFills',
            'breakdown': 'adUnits,date',
        }
        
        url = f"{self.BASE_URL}{self.REPORT_ENDPOINT}"
        
        try:
            data = await self._get_json(url, headers=headers, params=params)
        except Exception as e:
            error_msg = str(e)
            if '401' in error_msg:
                raise Exception(
                    f"IronSource authentication failed (401). "
                    "Please check your username (email) and secret_key in config.yaml"
                )
            raise Exception(f"IronSource API error: {error_msg}")
        
        if not isinstance(data, list):
            if isinstance(data, dict) and ('error' in data or 'message' in data):
                raise Exception(f"IronSource API error: {data}")
            return platform_data
        
        for item in data:
            if not isinstance(item, dict):
                continue
            
            ad_units_raw = item.get('adUnits', '')
            ad_type = self.AD_TYPE_MAP.get(ad_units_raw)
            
            # Skip unsupported ad types (e.g., Offerwall)
            if ad_type is None:
                continue
            
            ad_key = ad_type.value
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
                platform_data['ad_data'][ad_key]['revenue'] += rev
                platform_data['ad_data'][ad_key]['impressions'] += imps
                platform_data['ad_data'][ad_key]['clicks'] += clks
                platform_data['ad_data'][ad_key]['requests'] += reqs
                platform_data['ad_data'][ad_key]['fills'] += fls
        
        # Calculate eCPMs
        platform_data['ecpm'] = self._calculate_ecpm(platform_data['revenue'], platform_data['impressions'])
        
        for ad_key in platform_data['ad_data']:
            ad_data = platform_data['ad_data'][ad_key]
            ad_data['ecpm'] = self._calculate_ecpm(ad_data['revenue'], ad_data['impressions'])
        
        return platform_data
    
    async def fetch_data(self, start_date: datetime, end_date: datetime) -> FetchResult:
        """
        Fetch revenue and impression data for the given date range.
        
        Args:
            start_date: Start date for data fetch
            end_date: End date for data fetch
            
        Returns:
            FetchResult containing revenue and impressions data
        """
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        # Initialize platform data
        platform_data = self._create_extended_platform_data()
        
        total_revenue = 0.0
        total_impressions = 0
        total_clicks = 0
        total_requests = 0
        total_fills = 0
        
        # Fetch data for Android apps
        if self.android_app_keys:
            android_data = await self._fetch_platform_data(
                start_str, end_str, self.android_app_keys, Platform.ANDROID
            )
            platform_data[Platform.ANDROID.value] = android_data
            
            total_revenue += android_data['revenue']
            total_impressions += android_data['impressions']
            total_clicks += android_data['clicks']
            total_requests += android_data['requests']
            total_fills += android_data['fills']
        
        # Fetch data for iOS apps
        if self.ios_app_keys:
            ios_data = await self._fetch_platform_data(
                start_str, end_str, self.ios_app_keys, Platform.IOS
            )
            platform_data[Platform.IOS.value] = ios_data
            
            total_revenue += ios_data['revenue']
            total_impressions += ios_data['impressions']
            total_clicks += ios_data['clicks']
            total_requests += ios_data['requests']
            total_fills += ios_data['fills']
        
        # Build result
        result = self._build_result(
            start_date, end_date,
            revenue=total_revenue,
            impressions=total_impressions,
            platform_data=platform_data,
            requests=total_requests,
            fills=total_fills,
            clicks=total_clicks
        )
        
        return result
    
    def get_network_name(self) -> str:
        """Return the name of the network."""
        return NetworkName.IRONSOURCE.display_name
    
    def get_network_enum(self) -> NetworkName:
        """Return the NetworkName enum."""
        return NetworkName.IRONSOURCE
