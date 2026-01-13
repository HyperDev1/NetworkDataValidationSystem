"""
Meta Audience Network data fetcher implementation.
Async version using aiohttp with retry support.
API Docs: https://developers.facebook.com/docs/audience-network/optimization/report-api/guide-v2/
"""
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from .base_fetcher import NetworkDataFetcher, FetchResult
from ..enums import Platform, AdType, NetworkName


logger = logging.getLogger(__name__)


class MetaFetcher(NetworkDataFetcher):
    """Fetcher for Meta Audience Network monetization data."""
    
    # Graph API version
    API_VERSION = "v24.0"
    
    # Meta Audience Network reporting delay:
    # Using T-1 to get more recent data (previous day)
    # Note: Data may still be finalizing but is usually accurate enough
    DATA_DELAY_DAYS = 1
    
    # Ad format mapping - Meta placement to AdType enum
    AD_FORMAT_MAP = {
        'banner': AdType.BANNER,
        'medium_rectangle': AdType.BANNER,
        'interstitial': AdType.INTERSTITIAL,
        'rewarded_video': AdType.REWARDED,
        'rewarded_interstitial': AdType.REWARDED,
        'rewarded': AdType.REWARDED,
        'native': AdType.BANNER,
        'native_banner': AdType.BANNER,
    }
    
    # Platform mapping
    PLATFORM_MAP = {
        'android': Platform.ANDROID,
        'ios': Platform.IOS,
        'all': Platform.ANDROID,  # Fallback
    }
    
    def __init__(
        self,
        access_token: str,
        business_id: str
    ):
        """
        Initialize Meta Audience Network fetcher.
        
        Args:
            access_token: Meta System User Access Token
            business_id: Meta Business ID
        """
        super().__init__()
        self.access_token = access_token
        self.business_id = business_id
        self.base_url = f"https://graph.facebook.com/{self.API_VERSION}"
    
    def _normalize_ad_format(self, placement: str) -> AdType:
        """Normalize ad format from placement name to AdType enum."""
        if not placement:
            return AdType.INTERSTITIAL
        
        placement_lower = placement.lower().strip()
        
        # Direct mapping check
        if placement_lower in self.AD_FORMAT_MAP:
            return self.AD_FORMAT_MAP[placement_lower]
        
        # Keyword-based detection
        if 'banner' in placement_lower:
            return AdType.BANNER
        elif 'reward' in placement_lower:
            return AdType.REWARDED
        elif 'interstitial' in placement_lower:
            return AdType.INTERSTITIAL
        elif 'native' in placement_lower:
            return AdType.BANNER
        
        return AdType.INTERSTITIAL
    
    async def _poll_async_results(self, query_id: str, max_attempts: int = 10) -> list:
        """
        Poll for async query results using adnetworkanalytics_results endpoint.
        
        Args:
            query_id: The async query ID
            max_attempts: Maximum polling attempts
            
        Returns:
            List of result data
        """
        # Use adnetworkanalytics_results endpoint
        results_url = f"{self.base_url}/{self.business_id}/adnetworkanalytics_results"
        params = {
            "access_token": self.access_token,
            "query_ids": json.dumps([query_id])
        }
        
        for attempt in range(max_attempts):
            logger.debug(f"Meta polling attempt {attempt + 1}/{max_attempts}...")
            
            try:
                data = await self._get_json(results_url, params=params)
                
                results_data = data.get('data', [])
                
                if results_data:
                    # Check if query is complete
                    for item in results_data:
                        status = item.get('status', '')
                        logger.debug(f"Meta query status: {status}")
                        
                        if status == 'complete':
                            # Return the results
                            results = item.get('results', [])
                            logger.debug(f"Meta results count: {len(results) if results else 0}")
                            return results
                        elif status in ['failed', 'error']:
                            raise Exception(f"Meta query failed: {item}")
                
            except Exception as e:
                if 'query failed' in str(e).lower():
                    raise
                logger.debug(f"Meta poll error: {e}")
            
            # Wait before next poll
            await asyncio.sleep(2)
        
        raise Exception("Meta query polling timed out")
    
    def _process_metric_row(
        self, 
        row: dict, 
        ad_data: dict, 
        platform_data: dict
    ) -> tuple:
        """
        Process a single metric row from Meta API.
        
        Args:
            row: Single row from API results
            ad_data: Ad type aggregated data
            platform_data: Platform aggregated data
            
        Returns:
            Tuple of (revenue_added, impressions_added)
        """
        revenue_added = 0.0
        impressions_added = 0
        
        try:
            metric = row.get('metric', '')
            value = float(row.get('value', 0) or 0)
            
            # Get breakdowns - list format: [{"key": "platform", "value": "android"}, ...]
            breakdowns = row.get('breakdowns', [])
            breakdowns_dict = {}
            if isinstance(breakdowns, list):
                breakdowns_dict = {b.get('key'): b.get('value') for b in breakdowns if 'key' in b}
            
            platform_raw = breakdowns_dict.get('platform', 'android')
            display_format = breakdowns_dict.get('display_format', 'interstitial')
            
            platform = self._normalize_platform(str(platform_raw))
            ad_format = self._normalize_ad_format(str(display_format))
            
            plat_key = platform.value
            ad_key = ad_format.value
            
            # Only process revenue and impression metrics
            if metric == 'fb_ad_network_revenue':
                ad_data[ad_key]['revenue'] += value
                platform_data[plat_key]['ad_data'][ad_key]['revenue'] += value
                platform_data[plat_key]['revenue'] += value
                revenue_added = value
            elif metric == 'fb_ad_network_imp':
                int_value = int(value)
                ad_data[ad_key]['impressions'] += int_value
                platform_data[plat_key]['ad_data'][ad_key]['impressions'] += int_value
                platform_data[plat_key]['impressions'] += int_value
                impressions_added = int_value
            # Skip cpm - we calculate it ourselves
            
        except (TypeError, ValueError, KeyError) as e:
            logger.debug(f"Meta row process error: {str(e)}")
        
        return revenue_added, impressions_added
    
    async def fetch_data(self, start_date: datetime, end_date: datetime) -> FetchResult:
        """
        Fetch data from Meta Audience Network Reporting API v2.
        
        Args:
            start_date: Start date for data fetch
            end_date: End date for data fetch
            
        Returns:
            FetchResult containing revenue, impressions, ecpm data
        """
        logger.debug("Fetching Meta Audience Network data (T-3 daily mode)...")
        
        # Ensure we don't exceed Meta's 8-day limit
        range_days = (end_date - start_date).days + 1
        if range_days > 8:
            start_date = end_date - timedelta(days=7)  # 8 days total
            range_days = 8
        
        logger.debug(f"Meta date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({range_days} days)")
        
        # Initialize data structures using base class helpers
        ad_data = self._init_ad_data()
        platform_data = self._init_platform_data()
        
        total_revenue = 0.0
        total_impressions = 0
        
        # GET /{business_id}/adnetworkanalytics
        query_url = f"{self.base_url}/{self.business_id}/adnetworkanalytics"
        
        # Query parameters
        query_params = {
            "access_token": self.access_token,
            "since": start_date.strftime("%Y-%m-%d"),
            "until": end_date.strftime("%Y-%m-%d"),
            "metrics": '["fb_ad_network_revenue","fb_ad_network_imp","fb_ad_network_cpm"]',
            "breakdowns": '["platform","display_format"]',
            "aggregation_period": "day",
        }
        
        try:
            query_response = await self._get_json(query_url, params=query_params)
            
            # Check for async query - need to poll for results
            query_id = query_response.get('query_id')
            async_result_link = query_response.get('async_result_link')
            
            if query_id and async_result_link:
                logger.debug(f"Meta async query created, ID: {query_id}")
                data = await self._poll_async_results(query_id)
            else:
                # Direct data in response
                data = query_response.get('data', [])
            
        except Exception as e:
            raise Exception(f"Failed to fetch data from Meta Audience Network: {str(e)}")
        
        # Parse response data
        if not data:
            logger.debug("Meta returned no data.")
        else:
            logger.debug(f"Meta got {len(data)} data entries")
        
        # Process results
        results = data if isinstance(data, list) else [data] if data else []
        
        for entry in results:
            try:
                # Handle nested results structure from query response
                if 'results' in entry:
                    for row in entry.get('results', []):
                        rev, imps = self._process_metric_row(row, ad_data, platform_data)
                        total_revenue += rev
                        total_impressions += imps
            except (TypeError, ValueError, KeyError) as e:
                logger.debug(f"Meta entry parse error: {str(e)}")
                continue
        
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
        
        logger.debug(f"Meta Total: ${result['revenue']:.2f} revenue, {result['impressions']:,} impressions")
        
        return result
    
    def get_network_name(self) -> str:
        """Return the network name."""
        return NetworkName.META.display_name
    
    def get_network_enum(self) -> NetworkName:
        """Return the NetworkName enum."""
        return NetworkName.META

