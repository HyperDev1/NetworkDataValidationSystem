"""
BidMachine SSP data fetcher implementation.
Async version using aiohttp with retry support.
API Docs: https://developers.bidmachine.io/reporting-api/retrieve-ssp-report-data
"""
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

import aiohttp

from .base_fetcher import NetworkDataFetcher, FetchResult
from ..enums import Platform, AdType, NetworkName


logger = logging.getLogger(__name__)


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
        'ios': Platform.IOS,
        'android': Platform.ANDROID,
        'IOS': Platform.IOS,
        'ANDROID': Platform.ANDROID,
    }
    
    # Ad type mapping - BidMachine ad_type to AdType enum
    AD_TYPE_MAP = {
        # Banner
        'banner': AdType.BANNER,
        'native': AdType.BANNER,
        'mrec': AdType.BANNER,
        # Interstitial
        'interstitial': AdType.INTERSTITIAL,
        'fullscreen': AdType.INTERSTITIAL,
        'non_skippable_interstitial': AdType.INTERSTITIAL,
        # Rewarded
        'rewarded': AdType.REWARDED,
        'fullscreen_rewarded': AdType.REWARDED,
        'skippable_video': AdType.REWARDED,
        'non_skippable_video': AdType.REWARDED,
        'rewarded_video': AdType.REWARDED,
        'video': AdType.REWARDED,
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
        super().__init__()
        self.username = username
        self.password = password
        self.app_bundle_ids = [a.strip() for a in app_bundle_ids.split(',') if a.strip()] if app_bundle_ids else []
    
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
        # Note: BidMachine API uses exclusive end date, so we add 1 day
        start_str = start_date.strftime('%Y-%m-%d')
        api_end_date = end_date + timedelta(days=1)
        api_end_str = api_end_date.strftime('%Y-%m-%d')
        
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
        
        auth = aiohttp.BasicAuth(self.username, self.password)
        
        for attempt in range(max_retries):
            try:
                session = await self._get_session()
                async with session.get(
                    url,
                    params=params,
                    auth=auth,
                    timeout=aiohttp.ClientTimeout(total=300)
                ) as response:
                    if response.status == 401:
                        raise Exception("BidMachine API authentication failed. Please check your username and password.")
                    
                    if response.status == 429:
                        # Rate limited - wait and retry
                        if attempt < max_retries - 1:
                            wait_time = 15 * (attempt + 1)  # 15s, 30s, 45s
                            logger.warning(f"BidMachine rate limited, waiting {wait_time}s...")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            raise Exception("BidMachine API rate limit exceeded. Please try again later.")
                    
                    if response.status != 200:
                        text = await response.text()
                        raise Exception(f"BidMachine API error: {response.status} - {text[:500]}")
                    
                    response_text = await response.text()
                    break
                    
            except Exception as e:
                if attempt < max_retries - 1 and 'rate limit' not in str(e).lower():
                    logger.warning(f"BidMachine request failed (attempt {attempt + 1}): {e}")
                    await asyncio.sleep(5)
                    continue
                raise
        
        # Parse NDJSON response (newline-delimited JSON)
        rows = self._parse_ndjson_response(response_text)
        
        return self._parse_response(rows, start_date, end_date)
    
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
        start_date: datetime, 
        end_date: datetime
    ) -> FetchResult:
        """
        Parse BidMachine API response into standardized format.
        
        Args:
            rows: Parsed API response rows
            start_date: Start date for date range
            end_date: End date for date range
            
        Returns:
            FetchResult with standardized data
        """
        # Initialize data structures using base class helpers
        ad_data = self._init_ad_data()
        platform_data = self._init_platform_data()
        
        total_revenue = 0.0
        total_impressions = 0
        
        if not rows:
            result = self._build_result(
                start_date, end_date,
                revenue=total_revenue,
                impressions=total_impressions,
                ad_data=ad_data,
                platform_data=platform_data
            )
            self._finalize_ecpm(result, ad_data, platform_data)
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
            
            # Extract and normalize platform
            platform_raw = str(row.get('platform', 'android')).lower()
            platform = self._normalize_platform(platform_raw)
            
            # Extract and normalize ad type
            ad_type_raw = str(row.get('ad_type', 'banner')).lower()
            ad_type = self._normalize_ad_type(ad_type_raw)
            
            # Accumulate totals
            total_revenue += revenue
            total_impressions += impressions
            
            # Use base class helper to accumulate metrics
            self._accumulate_metrics(
                platform_data, ad_data,
                platform, ad_type,
                revenue, impressions
            )
        
        # Build result using base class helper
        result = self._build_result(
            start_date, end_date,
            revenue=total_revenue,
            impressions=total_impressions,
            ad_data=ad_data,
            platform_data=platform_data
        )
        
        # Finalize eCPM calculations
        self._finalize_ecpm(result, ad_data, platform_data)
        
        return result
    
    def get_network_name(self) -> str:
        """Return the name of the network."""
        return NetworkName.BIDMACHINE.display_name
    
    def get_network_enum(self) -> NetworkName:
        """Return the NetworkName enum."""
        return NetworkName.BIDMACHINE
