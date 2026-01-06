"""
Unity Ads Monetization Stats API data fetcher implementation.
API Docs: https://docs.unity.com/en-us/grow/ads/optimization/monetization-stats-api
"""
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional
from .base_fetcher import NetworkDataFetcher


class UnityAdsFetcher(NetworkDataFetcher):
    """Fetcher for Unity Ads Monetization Stats API data."""
    
    # Ad format mapping - Unity Ads format to our standard categories
    AD_FORMAT_MAP = {
        'banner': 'banner',
        'interstitial': 'interstitial',
        'rewarded': 'rewarded',
        'rewarded_video': 'rewarded',
        'rewardedvideo': 'rewarded',
        'video': 'interstitial',
    }
    
    # Platform mapping
    PLATFORM_MAP = {
        'android': 'android',
        'ios': 'ios',
        'google': 'android',
        'apple': 'ios',
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
        self.api_key = api_key
        self.organization_id = organization_id
        self.game_ids = [g.strip() for g in game_ids.split(',') if g.strip()] if game_ids else []
        # Unity Ads Monetization Stats API endpoint
        # Docs: https://docs.unity.com/en-us/grow/ads/optimization/monetization-stats-api
        self.base_url = "https://monetization.api.unity.com/stats/v1/operate/organizations"
    
    def _normalize_platform(self, platform: str) -> str:
        """Normalize platform name to standard format."""
        if not platform:
            return 'android'
        
        platform_lower = platform.lower().strip()
        return self.PLATFORM_MAP.get(platform_lower, 'android')
    
    def _normalize_ad_format(self, ad_format: str) -> str:
        """Normalize ad format to standard category."""
        if not ad_format:
            return 'interstitial'
        
        ad_format_lower = ad_format.lower().strip()
        return self.AD_FORMAT_MAP.get(ad_format_lower, 'interstitial')
    
    def _init_ad_data(self) -> Dict[str, Dict[str, Any]]:
        """Initialize empty ad data structure."""
        return {
            'banner': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0},
            'interstitial': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0},
            'rewarded': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0}
        }
    
    def _init_platform_data(self) -> Dict[str, Any]:
        """Initialize empty platform data structure."""
        return {
            'android': {
                'ad_data': self._init_ad_data(),
                'revenue': 0.0,
                'impressions': 0,
                'ecpm': 0.0
            },
            'ios': {
                'ad_data': self._init_ad_data(),
                'revenue': 0.0,
                'impressions': 0,
                'ecpm': 0.0
            }
        }
    
    def _calculate_ecpm(self, revenue: float, impressions: int) -> float:
        """Calculate eCPM from revenue and impressions."""
        if impressions <= 0:
            return 0.0
        return round((revenue / impressions) * 1000, 2)
    
    def _finalize_ecpm(self, data: Dict[str, Any]):
        """Calculate and update eCPM values in data structure."""
        # Ad data eCPM
        if 'ad_data' in data:
            for key in data['ad_data']:
                imp = data['ad_data'][key]['impressions']
                rev = data['ad_data'][key]['revenue']
                data['ad_data'][key]['ecpm'] = self._calculate_ecpm(rev, imp)
                data['ad_data'][key]['revenue'] = round(rev, 2)
        
        # Platform data eCPM
        if 'platform_data' in data:
            for plat in data['platform_data']:
                plat_data = data['platform_data'][plat]
                plat_data['ecpm'] = self._calculate_ecpm(plat_data['revenue'], plat_data['impressions'])
                plat_data['revenue'] = round(plat_data['revenue'], 2)
                
                for key in plat_data.get('ad_data', {}):
                    aimp = plat_data['ad_data'][key]['impressions']
                    arev = plat_data['ad_data'][key]['revenue']
                    plat_data['ad_data'][key]['ecpm'] = self._calculate_ecpm(arev, aimp)
                    plat_data['ad_data'][key]['revenue'] = round(arev, 2)
    
    def _extract_ad_format_from_placement(self, placement: str) -> str:
        """
        Extract ad format from Unity placement name.
        
        Placement names: Banner_IOS, Interstitial_IOS, Rewarded_IOS, 
                        Banner_DRD, Interstitial_DRD, Rewarded_DRD
        """
        if not placement:
            return 'interstitial'
        
        placement_lower = placement.lower()
        
        if 'banner' in placement_lower:
            return 'banner'
        elif 'rewarded' in placement_lower:
            return 'rewarded'
        elif 'interstitial' in placement_lower:
            return 'interstitial'
        else:
            return 'interstitial'
    
    def fetch_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Fetch data from Unity Ads Monetization Stats API.
        
        Args:
            start_date: Start date for data fetch
            end_date: End date for data fetch
            
        Returns:
            Dictionary containing revenue, impressions, ecpm data by platform and ad type
        """
        # Build API URL - Using the Monetization Stats API
        # Docs: https://docs.unity.com/en-us/grow/ads/optimization/monetization-stats-api
        # GET https://monetization.api.unity.com/stats/v1/operate/organizations/<organizationId>
        api_url = f"{self.base_url}/{self.organization_id}"
        
        # Headers
        headers = {
            "Accept": "application/json"
        }
        
        # Query parameters - according to Unity Ads Monetization Stats API docs
        # API key is passed as 'apikey' query parameter
        # groupBy valid values: source, placement, country, platform, game
        # Using game,platform,placement to get ad format breakdown
        # Date format: ISO 8601 with time (e.g., 2025-12-26T00:00:00Z to 2025-12-26T23:59:00Z)
        # This format is required to fetch data for specific days correctly
        params = {
            "apikey": self.api_key,
            "start": start_date.strftime("%Y-%m-%dT00:00:00Z"),
            "end": end_date.strftime("%Y-%m-%dT23:59:00Z"),
            "scale": "day",
            "groupBy": "game,platform,placement",
            "fields": "revenue_sum,start_count,view_count",
        }
        
        # Filter by game IDs if specified
        if self.game_ids:
            params["gameIds"] = ",".join(self.game_ids)
        
        print(f"      [DEBUG] Unity Ads API URL: {api_url}")
        print(f"      [DEBUG] Unity Ads params: {params}")
        
        try:
            response = requests.get(api_url, headers=headers, params=params, timeout=30)
            
            print(f"      [DEBUG] Unity Ads response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"      [DEBUG] Unity Ads response: {response.text[:500]}")
            
            response.raise_for_status()
            data = response.json()
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch data from Unity Ads: {str(e)}")
        
        # Initialize data structures
        ad_data = self._init_ad_data()
        platform_data = self._init_platform_data()
        
        total_revenue = 0.0
        total_impressions = 0
        
        # Parse response data
        rows = data if isinstance(data, list) else data.get('results', data.get('data', data.get('rows', [])))
        
        if not rows:
            print(f"      [DEBUG] Unity Ads returned no data. Response: {str(data)[:200]}")
        else:
            print(f"      [DEBUG] Unity Ads got {len(rows)} rows")
            if rows:
                print(f"      [DEBUG] Unity Ads sample row: {rows[0]}")
        
        for row in rows:
            try:
                # Skip rows with null placement (aggregate rows)
                placement = row.get('placement')
                if not placement:
                    continue
                
                # Extract metrics - Unity Monetization Stats API field names
                revenue = float(row.get('revenue_sum', row.get('revenue', 0)) or 0)
                impressions = int(row.get('start_count', row.get('view_count', row.get('impressions', 0))) or 0)
                
                # Get platform from 'platform' field
                platform_raw = row.get('platform', '')
                platform = self._normalize_platform(platform_raw)
                
                # Extract ad format from placement name
                # Placement names: Banner_IOS, Interstitial_IOS, Rewarded_IOS, Banner_DRD, Interstitial_DRD, Rewarded_DRD
                ad_format = self._extract_ad_format_from_placement(placement)
                
                # Accumulate totals
                total_revenue += revenue
                total_impressions += impressions
                
                # Accumulate by ad type
                ad_data[ad_format]['revenue'] += revenue
                ad_data[ad_format]['impressions'] += impressions
                
                # Accumulate by platform
                platform_data[platform]['ad_data'][ad_format]['revenue'] += revenue
                platform_data[platform]['ad_data'][ad_format]['impressions'] += impressions
                platform_data[platform]['revenue'] += revenue
                platform_data[platform]['impressions'] += impressions
                
            except (TypeError, ValueError, KeyError) as e:
                print(f"      [DEBUG] Unity Ads row parse error: {str(e)}, row: {row}")
                continue
        
        # Build result
        result = {
            'revenue': round(total_revenue, 2),
            'impressions': total_impressions,
            'ecpm': self._calculate_ecpm(total_revenue, total_impressions),
            'ad_data': ad_data,
            'platform_data': platform_data,
            'network': self.get_network_name(),
            'date_range': {
                'start': start_date.strftime("%Y-%m-%d"),
                'end': end_date.strftime("%Y-%m-%d")
            }
        }
        
        # Calculate all eCPM values
        self._finalize_ecpm(result)
        
        return result
    
    def get_network_name(self) -> str:
        """Return the network name."""
        return "Unity Bidding"

