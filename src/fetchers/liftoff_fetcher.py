"""
Liftoff (formerly Vungle) Publisher Reporting API 2.0 data fetcher implementation.
Async version using aiohttp with retry support.
API Docs: https://support.vungle.com/hc/en-us/articles/211365828-Publisher-Reporting-API-2-0
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from .base_fetcher import NetworkDataFetcher, FetchResult
from ..enums import Platform, AdType, NetworkName


logger = logging.getLogger(__name__)


class LiftoffFetcher(NetworkDataFetcher):
    """Fetcher for Liftoff (Vungle) publisher data using Reporting API 2.0."""
    
    # Liftoff API endpoints
    BASE_URL = "https://report.api.vungle.com"
    REPORT_ENDPOINT = "/ext/pub/reports/performance"
    
    # Platform mapping - Vungle returns "iOS"/"Android"
    PLATFORM_MAP = {
        'iOS': Platform.IOS,
        'ios': Platform.IOS,
        'Android': Platform.ANDROID,
        'android': Platform.ANDROID,
    }
    
    # Ad type mapping
    AD_TYPE_MAP = {
        'banner': AdType.BANNER,
        'video': AdType.INTERSTITIAL,  # default for video, override with incentivized
    }
    
    def __init__(
        self,
        api_key: str,
        application_ids: Optional[str] = None,
    ):
        """
        Initialize Liftoff fetcher.
        
        Args:
            api_key: Liftoff API Key from Dashboard → Reports page
            application_ids: Optional comma-separated Liftoff Application IDs to filter
        """
        super().__init__()
        self.api_key = api_key
        self.application_ids = application_ids
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Generate Bearer Token header for Liftoff API.
        
        Returns:
            Dictionary with Authorization and required headers
        """
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Vungle-Version': '1',
            'Accept': 'application/json',
        }
    
    async def _fetch_report_data(
        self,
        start_date: str,
        end_date: str,
    ) -> List[Dict[str, Any]]:
        """
        Fetch report data from Liftoff API.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            List of report data rows
        """
        headers = self._get_auth_headers()
        
        # Build query parameters
        # Dimensions: date, platform, adType, incentivized (for ad type breakdown)
        # - date: for daily breakdown (YYYY-MM-DD)
        # - adType: "banner" or "video"
        # - incentivized: true (rewarded) or false (interstitial) - only applies to video
        # Aggregates: impressions, revenue, clicks, ecpm
        params = {
            'start': start_date,
            'end': end_date,
            'dimensions': 'date,platform,adType,incentivized',
            'aggregates': 'impressions,revenue,clicks,ecpm',
        }
        
        # Add application filter if specified
        if self.application_ids:
            params['applicationId'] = self.application_ids
        
        url = f"{self.BASE_URL}{self.REPORT_ENDPOINT}"
        
        try:
            data = await self._get_json(url, headers=headers, params=params)
        except Exception as e:
            error_str = str(e)
            if '401' in error_str:
                raise Exception(
                    f"Liftoff authentication failed (401). "
                    "Please check your api_key in config.yaml. "
                    "Get your API key from Liftoff Dashboard → Reports page."
                )
            raise Exception(f"Liftoff API error: {error_str}")
        
        # Parse response
        if not data:
            return []
        
        if not isinstance(data, list):
            # Might be an error object
            if isinstance(data, dict) and ('error' in data or 'message' in data):
                raise Exception(f"Liftoff API error: {data}")
            return []
        
        return data
    
    def _process_report_data(
        self, 
        report_data: List[Dict[str, Any]],
        ad_data: Dict,
        platform_data: Dict,
        daily_data: Dict
    ) -> tuple:
        """
        Process report data and aggregate by platform with daily breakdown.
        
        Args:
            report_data: List of report rows from API
            ad_data: Ad data dict to populate
            platform_data: Platform data dict to populate
            daily_data: Daily breakdown dict to populate
            
        Returns:
            Tuple of (total_revenue, total_impressions)
        """
        total_revenue = 0.0
        total_impressions = 0
        
        for row in report_data:
            if not isinstance(row, dict):
                continue
            
            # Get date from response (format: YYYY-MM-DD)
            date_key = row.get('date', '')
            if not date_key:
                date_key = 'unknown'
            
            # Get platform (iOS/Android)
            platform_raw = row.get('platform', '')
            platform = self._normalize_platform(platform_raw)
            
            # Determine ad type from adType and incentivized fields
            # - adType="banner" → banner
            # - adType="video" + incentivized=true → rewarded
            # - adType="video" + incentivized=false → interstitial
            ad_type_raw = row.get('adType', '').lower()
            incentivized = row.get('incentivized')
            
            if ad_type_raw == 'banner':
                ad_type = AdType.BANNER
            elif ad_type_raw == 'video':
                if incentivized is True or incentivized == 'true':
                    ad_type = AdType.REWARDED
                else:
                    ad_type = AdType.INTERSTITIAL
            else:
                # Unknown ad type, default to interstitial
                ad_type = AdType.INTERSTITIAL
            
            # Extract metrics
            rev = float(row.get('revenue', 0) or 0)
            imps = int(row.get('impressions', 0) or 0)
            
            # Accumulate totals
            total_revenue += rev
            total_impressions += imps
            
            # Use base class helper to accumulate metrics
            self._accumulate_metrics(
                platform_data, ad_data,
                platform, ad_type,
                rev, imps
            )
            
            # Accumulate daily breakdown
            if date_key not in daily_data:
                daily_data[date_key] = {}
            if platform.value not in daily_data[date_key]:
                daily_data[date_key][platform.value] = {}
            if ad_type.value not in daily_data[date_key][platform.value]:
                daily_data[date_key][platform.value][ad_type.value] = {'revenue': 0.0, 'impressions': 0}
            
            daily_data[date_key][platform.value][ad_type.value]['revenue'] += rev
            daily_data[date_key][platform.value][ad_type.value]['impressions'] += imps
        
        return total_revenue, total_impressions
    
    async def fetch_data(self, start_date: datetime, end_date: datetime) -> FetchResult:
        """
        Fetch revenue and impression data for the given date range.
        
        Args:
            start_date: Start date for data fetch
            end_date: End date for data fetch
            
        Returns:
            FetchResult containing revenue and impressions data
        """
        # Format dates as YYYY-MM-DD
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        # Initialize data structures using base class helpers
        ad_data = self._init_ad_data()
        platform_data = self._init_platform_data()
        
        # Daily breakdown data: {date_str: {platform: {ad_type: {revenue, impressions}}}}
        daily_data = {}
        
        # Fetch report data
        report_data = await self._fetch_report_data(start_str, end_str)
        
        # Process and aggregate data
        total_revenue, total_impressions = self._process_report_data(
            report_data, ad_data, platform_data, daily_data
        )
        
        # Build result using base class helper
        result = self._build_result(
            start_date, end_date,
            revenue=total_revenue,
            impressions=total_impressions,
            ad_data=ad_data,
            platform_data=platform_data
        )
        
        # Add daily breakdown data for 7-day comparison
        result['daily_data'] = daily_data
        
        # Finalize eCPM calculations
        self._finalize_ecpm(result, ad_data, platform_data)
        
        return result
    
    def get_network_name(self) -> str:
        """Return the name of the network."""
        return NetworkName.LIFTOFF.display_name
    
    def get_network_enum(self) -> NetworkName:
        """Return the NetworkName enum."""
        return NetworkName.LIFTOFF
