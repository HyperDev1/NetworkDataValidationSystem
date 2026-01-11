"""
Liftoff (formerly Vungle) Publisher Reporting API 2.0 data fetcher implementation.
API Docs: https://support.vungle.com/hc/en-us/articles/211365828-Publisher-Reporting-API-2-0
"""
import requests
from datetime import datetime
from typing import Dict, Any, Optional, List
from .base_fetcher import NetworkDataFetcher


class LiftoffFetcher(NetworkDataFetcher):
    """Fetcher for Liftoff (Vungle) publisher data using Reporting API 2.0."""
    
    # Liftoff API endpoints
    BASE_URL = "https://report.api.vungle.com"
    REPORT_ENDPOINT = "/ext/pub/reports/performance"
    
    # Platform mapping - Vungle returns "iOS"/"Android"
    PLATFORM_MAP = {
        'iOS': 'ios',
        'ios': 'ios',
        'Android': 'android',
        'android': 'android',
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
    
    def _create_empty_platform_data(self) -> Dict[str, Any]:
        """Create empty platform data structure."""
        return {
            'revenue': 0.0,
            'impressions': 0,
            'ecpm': 0.0,
            'clicks': 0,
            'ad_data': {
                'banner': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0, 'clicks': 0},
                'interstitial': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0, 'clicks': 0},
                'rewarded': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0, 'clicks': 0},
            }
        }
    
    def _fetch_report_data(
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
        # Dimensions: platform, adType, incentivized (for ad type breakdown)
        # - adType: "banner" or "video"
        # - incentivized: true (rewarded) or false (interstitial) - only applies to video
        # Aggregates: impressions, revenue, clicks, ecpm
        params = {
            'start': start_date,
            'end': end_date,
            'dimensions': 'platform,adType,incentivized',
            'aggregates': 'impressions,revenue,clicks,ecpm',
        }
        
        # Add application filter if specified
        if self.application_ids:
            params['applicationId'] = self.application_ids
        
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
                f"Liftoff authentication failed (401).{error_detail} "
                "Please check your api_key in config.yaml. "
                "Get your API key from Liftoff Dashboard → Reports page."
            )
        
        if response.status_code != 200:
            error_msg = f"Liftoff API error: {response.status_code}"
            try:
                error_data = response.json()
                error_msg += f" - {error_data}"
            except:
                error_msg += f" - {response.text[:500]}"
            raise Exception(error_msg)
        
        # Parse response
        try:
            # Empty response returns empty list or empty string
            if not response.text or response.text.strip() == '':
                return []
            data = response.json()
            if not isinstance(data, list):
                # Might be an error object
                if isinstance(data, dict) and ('error' in data or 'message' in data):
                    raise Exception(f"Liftoff API error: {data}")
                return []
            return data
        except Exception as e:
            if 'Liftoff API error' in str(e):
                raise
            raise Exception(f"Failed to parse Liftoff response: {e}")
    
    def _process_report_data(self, report_data: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Process report data and aggregate by platform.
        
        Args:
            report_data: List of report rows from API
            
        Returns:
            Dictionary with platform_data structure
        """
        platform_data = {
            'android': self._create_empty_platform_data(),
            'ios': self._create_empty_platform_data(),
        }
        
        for row in report_data:
            if not isinstance(row, dict):
                continue
            
            # Get platform (iOS/Android)
            platform_raw = row.get('platform', '')
            platform = self.PLATFORM_MAP.get(platform_raw)
            
            if platform is None:
                continue
            
            # Determine ad type from adType and incentivized fields
            # - adType="banner" → banner
            # - adType="video" + incentivized=true → rewarded
            # - adType="video" + incentivized=false → interstitial
            ad_type_raw = row.get('adType', '').lower()
            incentivized = row.get('incentivized')
            
            if ad_type_raw == 'banner':
                ad_type = 'banner'
            elif ad_type_raw == 'video':
                if incentivized is True or incentivized == 'true':
                    ad_type = 'rewarded'
                else:
                    ad_type = 'interstitial'
            else:
                # Unknown ad type, default to interstitial
                ad_type = 'interstitial'
            
            # Extract metrics
            rev = float(row.get('revenue', 0) or 0)
            imps = int(row.get('impressions', 0) or 0)
            clks = int(row.get('clicks', 0) or 0)
            
            # Aggregate platform totals
            platform_data[platform]['revenue'] += rev
            platform_data[platform]['impressions'] += imps
            platform_data[platform]['clicks'] += clks
            
            # Aggregate by ad type
            platform_data[platform]['ad_data'][ad_type]['revenue'] += rev
            platform_data[platform]['ad_data'][ad_type]['impressions'] += imps
            platform_data[platform]['ad_data'][ad_type]['clicks'] += clks
        
        # Calculate eCPMs
        for platform in ['android', 'ios']:
            p_data = platform_data[platform]
            if p_data['impressions'] > 0:
                p_data['ecpm'] = (p_data['revenue'] / p_data['impressions']) * 1000
            
            for ad_type in ['banner', 'interstitial', 'rewarded']:
                ad_data = p_data['ad_data'][ad_type]
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
        
        # Fetch report data
        report_data = self._fetch_report_data(start_str, end_str)
        
        # Process and aggregate data
        platform_data = self._process_report_data(report_data)
        
        # Calculate totals
        total_revenue = 0.0
        total_impressions = 0
        total_clicks = 0
        
        for platform in ['android', 'ios']:
            total_revenue += platform_data[platform]['revenue']
            total_impressions += platform_data[platform]['impressions']
            total_clicks += platform_data[platform]['clicks']
        
        # Calculate overall eCPM
        total_ecpm = 0.0
        if total_impressions > 0:
            total_ecpm = (total_revenue / total_impressions) * 1000
        
        return {
            'revenue': total_revenue,
            'impressions': total_impressions,
            'ecpm': total_ecpm,
            'clicks': total_clicks,
            'network': self.get_network_name(),
            'date_range': {'start': start_str, 'end': end_str},
            'platform_data': platform_data,
        }
    
    def get_network_name(self) -> str:
        """Return the name of the network."""
        return "Liftoff Monetize Bidding"
