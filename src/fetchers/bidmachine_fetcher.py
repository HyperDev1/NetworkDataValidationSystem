"""
BidMachine SSP data fetcher implementation.
Uses BidMachine Reporting API for fetching monetization data.
API Docs: https://developers.bidmachine.io/reporting-api/retrieve-ssp-report-data
"""
import json
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from .base_fetcher import NetworkDataFetcher


class BidMachineFetcher(NetworkDataFetcher):
    """Fetcher for BidMachine SSP monetization data."""
    
    # BidMachine API endpoint
    BASE_URL = "https://api-eu.bidmachine.io"
    REPORT_ENDPOINT = "/api/v1/report/ssp"
    
    # Rate limit: 6 requests per minute
    # Max date range: 45 days
    # Request timeout: up to 300 seconds
    
    # Platform mapping
    PLATFORM_MAP = {
        'ios': 'ios',
        'android': 'android',
        'IOS': 'ios',
        'ANDROID': 'android',
    }
    
    # Ad type mapping - BidMachine ad_type to our standard categories
    # Based on BidMachine Ad Types:
    # - banner → banner
    # - interstitial, fullscreen, non_skippable_interstitial → interstitial
    # - fullscreen_rewarded, skippable_video, non_skippable_video → rewarded
    AD_TYPE_MAP = {
        # Banner
        'banner': 'banner',
        'native': 'banner',
        'mrec': 'banner',
        # Interstitial
        'interstitial': 'interstitial',
        'fullscreen': 'interstitial',
        'non_skippable_interstitial': 'interstitial',
        # Rewarded
        'rewarded': 'rewarded',
        'fullscreen_rewarded': 'rewarded',
        'skippable_video': 'rewarded',
        'non_skippable_video': 'rewarded',
        'rewarded_video': 'rewarded',
        'video': 'rewarded',
    }
    
    def __init__(
        self,
        username: str,
        password: str,
        app_bundle_ids: Optional[str] = None,
    ):
        """
        Initialize BidMachine fetcher.
        
        Args:
            username: BidMachine SSP account username (Basic Auth)
            password: BidMachine SSP account password (Basic Auth)
            app_bundle_ids: Optional comma-separated app bundle IDs to filter
        """
        self.username = username
        self.password = password
        self.app_bundle_ids = [a.strip() for a in app_bundle_ids.split(',') if a.strip()] if app_bundle_ids else []
    
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
        # Note: BidMachine API uses exclusive end date, so we add 1 day
        start_str = start_date.strftime('%Y-%m-%d')
        api_end_date = end_date + timedelta(days=1)
        api_end_str = api_end_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')  # For response metadata
        
        # Build query parameters
        params = {
            'start': start_str,
            'end': api_end_str,
            'format': 'json',
            'fields': 'date,app_bundle,platform,ad_type,impressions,clicks,ecpm,revenue'
        }
        
        # Make GET request with Basic Auth (with retry for rate limiting)
        url = f"{self.BASE_URL}{self.REPORT_ENDPOINT}"
        max_retries = 3
        
        for attempt in range(max_retries):
            response = requests.get(
                url,
                params=params,
                auth=(self.username, self.password),
                timeout=300  # Up to 5 min as per docs
            )
            
            if response.status_code == 401:
                raise Exception("BidMachine API authentication failed. Please check your username and password.")
            
            if response.status_code == 429:
                # Rate limited - wait and retry
                if attempt < max_retries - 1:
                    wait_time = 15 * (attempt + 1)  # 15s, 30s, 45s
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception("BidMachine API rate limit exceeded. Please try again later.")
            
            if response.status_code != 200:
                raise Exception(f"BidMachine API error: {response.status_code} - {response.text[:500]}")
            
            break
        
        # Parse NDJSON response (newline-delimited JSON)
        rows = self._parse_ndjson_response(response.text)
        
        return self._parse_response(rows, start_str, end_str)
    
    def _parse_ndjson_response(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Parse NDJSON (newline-delimited JSON) response.
        
        BidMachine returns each row as a separate JSON object on its own line.
        
        Args:
            response_text: Raw response text from API
            
        Returns:
            List of parsed JSON objects
        """
        rows = []
        lines = response_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    # Skip invalid lines
                    continue
        
        return rows
    
    def _parse_response(
        self, 
        rows: List[Dict[str, Any]], 
        start_str: str, 
        end_str: str
    ) -> Dict[str, Any]:
        """
        Parse BidMachine API response into standardized format.
        
        Response row format (from NDJSON):
        {
            "date": "2018-12-01",
            "country": "DE",
            "publisher_id": 6,
            "app_name": "App 1",
            "app_bundle": "111111111",
            "platform": "ios",
            "ad_type": "interstitial",
            "impressions": 271,
            "clicks": 19,
            "ctr": 7.01,
            "ecpm": 1.550635,
            "revenue": 0.420222
        }
        
        Args:
            rows: Parsed API response rows
            start_str: Start date string
            end_str: End date string
            
        Returns:
            Standardized data dictionary
        """
        # Initialize result structure
        result = {
            'revenue': 0.0,
            'impressions': 0,
            'ecpm': 0.0,
            'clicks': 0,
            'network': self.get_network_name(),
            'date_range': {'start': start_str, 'end': end_str},
            'platform_data': {
                'android': self._create_empty_platform_data(),
                'ios': self._create_empty_platform_data(),
            }
        }
        
        if not rows:
            return result
        
        for row in rows:
            if not isinstance(row, dict):
                continue
            
            # Filter by app_bundle_ids if specified
            app_bundle = str(row.get('app_bundle', ''))
            if self.app_bundle_ids and app_bundle not in self.app_bundle_ids:
                continue
            
            # Extract metrics
            revenue = float(row.get('revenue', 0) or 0)
            impressions = int(row.get('impressions', 0) or 0)
            clicks = int(row.get('clicks', 0) or 0)
            
            # Extract platform
            platform_raw = str(row.get('platform', 'android')).lower()
            platform = self.PLATFORM_MAP.get(platform_raw, 'android')
            
            # Ensure platform is valid
            if platform not in ['android', 'ios']:
                platform = 'android'
            
            # Extract ad type
            ad_type_raw = str(row.get('ad_type', 'banner')).lower()
            ad_type = self.AD_TYPE_MAP.get(ad_type_raw, 'banner')
            
            # Aggregate totals
            result['revenue'] += revenue
            result['impressions'] += impressions
            result['clicks'] += clicks
            
            # Aggregate by platform
            result['platform_data'][platform]['revenue'] += revenue
            result['platform_data'][platform]['impressions'] += impressions
            result['platform_data'][platform]['clicks'] += clicks
            
            # Aggregate by ad type within platform
            result['platform_data'][platform]['ad_data'][ad_type]['revenue'] += revenue
            result['platform_data'][platform]['ad_data'][ad_type]['impressions'] += impressions
            result['platform_data'][platform]['ad_data'][ad_type]['clicks'] += clicks
        
        # Calculate eCPMs
        if result['impressions'] > 0:
            result['ecpm'] = (result['revenue'] / result['impressions']) * 1000
        
        for platform in ['android', 'ios']:
            p_data = result['platform_data'][platform]
            if p_data['impressions'] > 0:
                p_data['ecpm'] = (p_data['revenue'] / p_data['impressions']) * 1000
            
            for ad_type in ['banner', 'interstitial', 'rewarded']:
                ad_data = p_data['ad_data'][ad_type]
                if ad_data['impressions'] > 0:
                    ad_data['ecpm'] = (ad_data['revenue'] / ad_data['impressions']) * 1000
        
        return result
    
    def get_network_name(self) -> str:
        """Return the name of the network."""
        return "BidMachine Bidding"
