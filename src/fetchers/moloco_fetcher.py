"""
Moloco Publisher Summary API data fetcher implementation.
Async version using aiohttp with token caching.
Uses Moloco Publisher Summary API for fetching monetization data.
API Docs: https://help.publisher.moloco.com/hc/en-us/articles/26777697929111-Get-performance-data-using-the-Publisher-Summary-API
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from .base_fetcher import NetworkDataFetcher, FetchResult
from ..enums import Platform, AdType, NetworkName
from ..utils import TokenCache


logger = logging.getLogger(__name__)


class MolocoFetcher(NetworkDataFetcher):
    """Fetcher for Moloco Publisher monetization data using Publisher Summary API."""
    
    # Moloco Publisher API endpoints
    AUTH_URL = "https://sdkpubapi.moloco.com/api/adcloud/publisher/v1/auth/tokens"
    SUMMARY_URL = "https://sdkpubapi.moloco.com/api/adcloud/publisher/v1/sdk/summary"
    
    # Ad type mapping - Moloco inventory_type to AdType enum
    AD_TYPE_MAP = {
        'BANNER': AdType.BANNER,
        'INTERSTITIAL': AdType.INTERSTITIAL,
        'REWARDED': AdType.REWARDED,
        'REWARDED_VIDEO': AdType.REWARDED,
        'REWARD_VIDEO': AdType.REWARDED,
        'REWARDED_INTERSTITIAL': AdType.REWARDED,
        'NATIVE': AdType.BANNER,
        'MREC': AdType.BANNER,
        'APP_OPEN': AdType.INTERSTITIAL,
        'APPOPEN': AdType.INTERSTITIAL,
    }
    
    # Platform mapping
    PLATFORM_MAP = {
        'ANDROID': Platform.ANDROID,
        'IOS': Platform.IOS,
        'android': Platform.ANDROID,
        'ios': Platform.IOS,
        'PLATFORM_TYPE_ANDROID': Platform.ANDROID,
        'PLATFORM_TYPE_IOS': Platform.IOS,
    }
    
    # Token cache key
    TOKEN_CACHE_KEY = "moloco"
    TOKEN_EXPIRES_IN = 3300  # 55 minutes (actual is 60, but with buffer)
    
    def __init__(
        self,
        email: str,
        password: str,
        platform_id: str,
        publisher_id: str,
        app_bundle_ids: Optional[str] = None,
        time_zone: str = "UTC",
        ad_unit_mapping: Optional[Dict[str, str]] = None
    ):
        """
        Initialize Moloco Publisher fetcher.
        
        Args:
            email: Moloco Publisher login email
            password: Moloco Publisher password
            platform_id: Moloco Platform ID (used as workplace_id for auth token)
            publisher_id: Moloco Publisher ID (used for API metric requests)
            app_bundle_ids: Optional comma-separated app bundle IDs to filter
            time_zone: Timezone for data aggregation (default: UTC)
            ad_unit_mapping: Optional dict mapping ad_unit_id to ad_type (banner/interstitial/rewarded)
        """
        super().__init__()
        self.email = email
        self.password = password
        self.platform_id = platform_id
        self.publisher_id = publisher_id
        self.app_bundle_ids = [a.strip() for a in app_bundle_ids.split(',') if a.strip()] if app_bundle_ids else []
        self.time_zone = time_zone
        self.ad_unit_mapping = ad_unit_mapping or {}
        self._token_cache = TokenCache()
        
    async def _get_access_token(self) -> str:
        """
        Get access token from cache or Moloco auth endpoint.
        Token is valid for 60 minutes.
        
        Returns:
            Access token string
        """
        # Check cache first
        cached = self._token_cache.get_token(self.TOKEN_CACHE_KEY)
        if cached:
            logger.debug("Using cached Moloco token")
            return cached['token']
        
        # Get new token via async request
        payload = {
            'email': self.email,
            'password': self.password,
            'workplace_id': self.platform_id,
        }
        
        try:
            data = await self._post_json(self.AUTH_URL, json=payload)
        except Exception as e:
            raise Exception(f"Moloco auth error: {str(e)}")
        
        # Check if password update is required
        token_type = data.get('token_type', '')
        if token_type == 'UPDATE_PASSWORD':
            raise Exception(
                "Moloco requires password update. "
                "Please log in to the Moloco Publisher Portal to update your password."
            )
        
        token = data.get('token')
        if not token:
            raise Exception(f"No token in response: {data}")
        
        # Cache the token
        self._token_cache.save_token(
            self.TOKEN_CACHE_KEY,
            token,
            expires_in=self.TOKEN_EXPIRES_IN
        )
        
        return token
    
    async def _make_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make POST request to Moloco Publisher Summary API.
        
        Args:
            payload: Request body (JSON payload)
            
        Returns:
            API response as dictionary
        """
        token = await self._get_access_token()
        
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}',
        }
        
        try:
            return await self._post_json(self.SUMMARY_URL, headers=headers, json=payload)
        except Exception as e:
            if '401' in str(e):
                # Token expired, clear cache and retry
                self._token_cache.delete_token(self.TOKEN_CACHE_KEY)
                token = await self._get_access_token()
                headers['Authorization'] = f'Bearer {token}'
                return await self._post_json(self.SUMMARY_URL, headers=headers, json=payload)
            raise
    
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
        
        payload = {
            'publisher_id': self.publisher_id,
            'date_range': {
                'start': start_str,
                'end': end_str
            },
            'dimensions': ['UTC_DATE', 'DEVICE_OS', 'AD_UNIT_ID'],
            'metrics': ['REVENUE', 'IMPRESSIONS', 'REQUESTS', 'FILLS', 'CLICKS'],
        }
        
        if self.app_bundle_ids:
            payload['dimension_filters'] = [
                {
                    'dimension': 'PUBLISHER_APP_STORE_ID',
                    'values': self.app_bundle_ids
                }
            ]
        
        response_data = await self._make_request(payload)
        return self._parse_response(response_data, start_date, end_date)
    
    def _parse_response(
        self, 
        response_data: Dict[str, Any], 
        start_date: datetime, 
        end_date: datetime
    ) -> FetchResult:
        """
        Parse Moloco API response into standardized format.
        """
        # Initialize data structures using base class helpers
        ad_data = self._init_ad_data()
        platform_data = self._init_platform_data()
        
        # Add extended metrics
        for plat in platform_data:
            platform_data[plat]['requests'] = 0
            platform_data[plat]['fills'] = 0
            platform_data[plat]['clicks'] = 0
            for ad_type in platform_data[plat]['ad_data']:
                platform_data[plat]['ad_data'][ad_type]['requests'] = 0
                platform_data[plat]['ad_data'][ad_type]['fills'] = 0
                platform_data[plat]['ad_data'][ad_type]['clicks'] = 0
        
        total_revenue = 0.0
        total_impressions = 0
        total_requests = 0
        total_fills = 0
        total_clicks = 0
        
        rows = response_data.get('rows', [])
        
        for row in rows:
            if not isinstance(row, dict):
                continue
            
            metric = row.get('metric', {})
            revenue = float(metric.get('revenue', 0) or 0)
            impressions_raw = metric.get('impressions', 0) or 0
            impressions = int(impressions_raw) if impressions_raw else 0
            requests_raw = metric.get('requests', 0) or 0
            requests = int(requests_raw) if requests_raw else 0
            clicks_raw = metric.get('clicks', 0) or 0
            clicks = int(clicks_raw) if clicks_raw else 0
            fill_rate = float(metric.get('fill_rate', 0) or 0)
            fills = int(requests * fill_rate) if requests > 0 else impressions
            
            # Extract platform using enum
            device = row.get('device', {})
            platform_raw = device.get('os', 'ANDROID')
            platform = self.PLATFORM_MAP.get(str(platform_raw).upper(), Platform.ANDROID)
            plat_key = platform.value
            
            # Extract ad type using enum
            ad_unit = row.get('ad_unit', {})
            ad_unit_id = ad_unit.get('ad_unit_id', '')
            
            if ad_unit_id and ad_unit_id in self.ad_unit_mapping:
                ad_type_str = self.ad_unit_mapping[ad_unit_id]
                ad_type = AdType.from_string(ad_type_str)
            else:
                inventory_type = ad_unit.get('inventory_type', '')
                ad_type = self.AD_TYPE_MAP.get(str(inventory_type).upper(), AdType.BANNER)
            
            ad_key = ad_type.value
            
            # Accumulate totals
            total_revenue += revenue
            total_impressions += impressions
            total_requests += requests
            total_fills += fills
            total_clicks += clicks
            
            # Accumulate by platform
            platform_data[plat_key]['revenue'] += revenue
            platform_data[plat_key]['impressions'] += impressions
            platform_data[plat_key]['requests'] += requests
            platform_data[plat_key]['fills'] += fills
            platform_data[plat_key]['clicks'] += clicks
            
            # Accumulate by ad type within platform
            platform_data[plat_key]['ad_data'][ad_key]['revenue'] += revenue
            platform_data[plat_key]['ad_data'][ad_key]['impressions'] += impressions
            platform_data[plat_key]['ad_data'][ad_key]['requests'] += requests
            platform_data[plat_key]['ad_data'][ad_key]['fills'] += fills
            platform_data[plat_key]['ad_data'][ad_key]['clicks'] += clicks
            
            # Also accumulate ad_data totals
            ad_data[ad_key]['revenue'] += revenue
            ad_data[ad_key]['impressions'] += impressions
        
        # Build result using base class helper
        result = self._build_result(
            start_date, end_date,
            revenue=total_revenue,
            impressions=total_impressions,
            ad_data=ad_data,
            platform_data=platform_data,
            requests=total_requests,
            fills=total_fills,
            clicks=total_clicks
        )
        
        # Finalize eCPM calculations
        self._finalize_ecpm(result, ad_data, platform_data)
        
        return result
    
    def get_network_name(self) -> str:
        """Return the name of the network."""
        return NetworkName.MOLOCO.display_name
    
    def get_network_enum(self) -> NetworkName:
        """Return the NetworkName enum."""
        return NetworkName.MOLOCO

