"""
Unity Ads Monetization Stats API data fetcher implementation.
Async version using aiohttp with retry support.
API Docs: https://docs.unity.com/en-us/grow/ads/optimization/monetization-stats-api
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from .base_fetcher import NetworkDataFetcher, FetchResult
from ..enums import Platform, AdType, NetworkName


logger = logging.getLogger(__name__)


class UnityAdsFetcher(NetworkDataFetcher):
    """Fetcher for Unity Ads Monetization Stats API data."""
    
    BASE_URL = "https://monetization.api.unity.com/stats/v1/operate/organizations"
    
    # Ad format mapping - Unity Ads format to AdType enum
    AD_FORMAT_MAP = {
        'banner': AdType.BANNER,
        'interstitial': AdType.INTERSTITIAL,
        'rewarded': AdType.REWARDED,
        'rewarded_video': AdType.REWARDED,
        'rewardedvideo': AdType.REWARDED,
        'video': AdType.INTERSTITIAL,
    }
    
    # Platform mapping
    PLATFORM_MAP = {
        'android': Platform.ANDROID,
        'ios': Platform.IOS,
        'google': Platform.ANDROID,
        'apple': Platform.IOS,
    }
    
    def __init__(
        self,
        api_key: str,
        organization_id: Optional[str] = None,
        game_ids: Optional[str] = None
    ):
        """
        Initialize Unity Ads fetcher.
        
        Args:
            api_key: Unity Ads Monetization Stats API Key
            organization_id: Optional Unity organization ID (for filtering)
            game_ids: Optional comma-separated game IDs to filter
        """
        super().__init__()
        self.api_key = api_key
        self.organization_id = organization_id
        self.game_ids = [g.strip() for g in game_ids.split(',') if g.strip()] if game_ids else []
    
    def _extract_ad_format_from_placement(self, placement: str) -> AdType:
        """
        Extract ad format from Unity placement name.
        
        Placement names: Banner_IOS, Interstitial_IOS, Rewarded_IOS, 
                        Banner_DRD, Interstitial_DRD, Rewarded_DRD
        """
        if not placement:
            return AdType.INTERSTITIAL
        
        placement_lower = placement.lower()
        
        if 'banner' in placement_lower:
            return AdType.BANNER
        elif 'rewarded' in placement_lower:
            return AdType.REWARDED
        elif 'interstitial' in placement_lower:
            return AdType.INTERSTITIAL
        else:
            return AdType.INTERSTITIAL
    
    async def fetch_data(self, start_date: datetime, end_date: datetime) -> FetchResult:
        """
        Fetch data from Unity Ads Monetization Stats API.
        
        Args:
            start_date: Start date for data fetch
            end_date: End date for data fetch
            
        Returns:
            FetchResult containing revenue, impressions, ecpm data by platform and ad type
        """
        # Build API URL
        api_url = f"{self.BASE_URL}/{self.organization_id}"
        
        # Headers
        headers = {"Accept": "application/json"}
        
        # Query parameters
        params = {
            "apikey": self.api_key,
            "start": start_date.strftime("%Y-%m-%dT00:00:00Z"),
            "end": end_date.strftime("%Y-%m-%dT23:59:00Z"),
            "scale": "day",
            "groupBy": "game,platform,placement",
            "fields": "revenue_sum,start_count,view_count",
        }
        
        if self.game_ids:
            params["gameIds"] = ",".join(self.game_ids)
        
        logger.debug(f"Unity Ads API URL: {api_url}")
        logger.debug(f"Unity Ads params: {params}")
        
        try:
            data = await self._get_json(api_url, headers=headers, params=params)
        except Exception as e:
            logger.error(f"Failed to fetch data from Unity Ads: {str(e)}")
            raise Exception(f"Failed to fetch data from Unity Ads: {str(e)}")
        
        # Initialize data structures using base class helpers
        ad_data = self._init_ad_data()
        platform_data = self._init_platform_data()
        
        total_revenue = 0.0
        total_impressions = 0
        
        # Parse response data
        rows = data if isinstance(data, list) else data.get('results', data.get('data', data.get('rows', [])))
        
        if not rows:
            logger.debug(f"Unity Ads returned no data. Response: {str(data)[:200]}")
        else:
            logger.debug(f"Unity Ads got {len(rows)} rows")
        
        for row in rows:
            try:
                # Skip rows with null placement (aggregate rows)
                placement = row.get('placement')
                if not placement:
                    continue
                
                # Extract metrics
                revenue = float(row.get('revenue_sum', row.get('revenue', 0)) or 0)
                impressions = int(row.get('start_count', row.get('view_count', row.get('impressions', 0))) or 0)
                
                # Get platform using enum
                platform_raw = row.get('platform', '')
                platform = self._normalize_platform(platform_raw)
                
                # Extract ad format from placement name
                ad_type = self._extract_ad_format_from_placement(placement)
                
                # Accumulate totals
                total_revenue += revenue
                total_impressions += impressions
                
                # Use base class helper to accumulate metrics
                self._accumulate_metrics(
                    platform_data, ad_data,
                    platform, ad_type,
                    revenue, impressions
                )
                
            except (TypeError, ValueError, KeyError) as e:
                logger.warning(f"Unity Ads row parse error: {str(e)}")
                continue
        
        # Build result using base class helper
        result = self._build_result(
            start_date, end_date,
            revenue=total_revenue,
            impressions=total_impressions,
            ad_data=ad_data,
            platform_data=platform_data
        )
        
        # Calculate all eCPM values
        self._finalize_ecpm(result, ad_data, platform_data)
        
        return result
    
    def get_network_name(self) -> str:
        """Return the network name."""
        return NetworkName.UNITY.display_name
    
    def get_network_enum(self) -> NetworkName:
        """Return the NetworkName enum."""
        return NetworkName.UNITY

