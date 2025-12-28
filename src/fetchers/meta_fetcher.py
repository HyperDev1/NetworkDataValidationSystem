"""
Meta Audience Network data fetcher implementation.
Uses Meta Audience Network Reporting API v2 for fetching monetization data.
API Docs: https://developers.facebook.com/docs/audience-network/optimization/report-api/guide-v2/
"""
import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional
from .base_fetcher import NetworkDataFetcher


class MetaFetcher(NetworkDataFetcher):
    """Fetcher for Meta Audience Network monetization data."""
    
    # Graph API version
    API_VERSION = "v24.0"
    
    # Meta Audience Network has a reporting delay of ~3 days
    # Data is only available starting from 3 days ago
    DATA_DELAY_DAYS = 3
    
    # Ad format mapping - Meta placement to our standard categories
    AD_FORMAT_MAP = {
        'banner': 'banner',
        'medium_rectangle': 'banner',
        'interstitial': 'interstitial',
        'rewarded_video': 'rewarded',
        'rewarded_interstitial': 'rewarded',
        'rewarded': 'rewarded',
        'native': 'banner',
        'native_banner': 'banner',
    }
    
    # Platform mapping
    PLATFORM_MAP = {
        'android': 'android',
        'ios': 'ios',
        'all': 'android',  # Fallback
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
        self.access_token = access_token
        self.business_id = business_id
        self.base_url = f"https://graph.facebook.com/{self.API_VERSION}"
    
    def _normalize_platform(self, platform: str) -> str:
        """Normalize platform name to standard format."""
        if not platform:
            return 'android'
        
        platform_lower = platform.lower().strip()
        return self.PLATFORM_MAP.get(platform_lower, 'android')
    
    def _normalize_ad_format(self, placement: str) -> str:
        """Normalize ad format from placement name to standard category."""
        if not placement:
            return 'interstitial'
        
        placement_lower = placement.lower().strip()
        
        # Direct mapping check
        if placement_lower in self.AD_FORMAT_MAP:
            return self.AD_FORMAT_MAP[placement_lower]
        
        # Keyword-based detection
        if 'banner' in placement_lower:
            return 'banner'
        elif 'reward' in placement_lower:
            return 'rewarded'
        elif 'interstitial' in placement_lower:
            return 'interstitial'
        elif 'native' in placement_lower:
            return 'banner'
        
        return 'interstitial'
    
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
    
    def fetch_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Fetch data from Meta Audience Network Reporting API v2.
        
        API Docs: https://developers.facebook.com/docs/audience-network/optimization/report-api/guide-v2/
        
        Note: Meta has a reporting delay of ~4 days. The caller (validation_service)
        is responsible for passing the correct shifted date range.
        Meta API has a maximum of 8 days limit for time range.
        
        Args:
            start_date: Start date for data fetch (UTC)
            end_date: End date for data fetch (UTC)
            
        Returns:
            Dictionary containing revenue, impressions, ecpm data by platform and ad type
        """
        print(f"      [INFO] Fetching Meta Audience Network data...")
        
        from datetime import timedelta
        
        # Ensure we don't exceed Meta's 8-day limit
        range_days = (end_date - start_date).days + 1
        if range_days > 8:
            start_date = end_date - timedelta(days=7)  # 8 days total
            range_days = 8
        
        print(f"      [INFO] Meta date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({range_days} days)")
        
        # GET /{business_id}/adnetworkanalytics
        query_url = f"{self.base_url}/{self.business_id}/adnetworkanalytics"
        
        # Query parameters - metrics and breakdowns as JSON arrays in URL
        # Date format: YYYY-MM-DD (according to Meta API docs)
        query_params = {
            "access_token": self.access_token,
            "since": start_date.strftime("%Y-%m-%dT00:00:00Z+0000"),
            "until": end_date.strftime("%Y-%m-%dT23:59:59Z+0000"),
            "metrics": '["fb_ad_network_revenue","fb_ad_network_imp","fb_ad_network_cpm"]',
            "breakdowns": '["platform","display_format"]',
        }
        
        print(f"      [DEBUG] Meta Query URL: {query_url}")
        print(f"      [DEBUG] Meta params:")
        print(f"         since: {query_params['since']}")
        print(f"         until: {query_params['until']}")
        print(f"         metrics: {query_params['metrics']}")
        print(f"         breakdowns: {query_params['breakdowns']}")
        
        try:
            # GET request
            response = requests.get(query_url, params=query_params, timeout=30)
            
            # Print full URL for debugging
            print(f"      [DEBUG] Full URL: {response.url}")
            print(f"      [DEBUG] Meta query response status: {response.status_code}")
            print(f"      [DEBUG] Meta query response: {response.text[:500]}")
            
            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get('error', {}).get('message', response.text[:500])
                print(f"      [ERROR] Meta API error: {error_msg}")
                raise Exception(f"Meta API error: {error_msg}")
            
            query_response = response.json()
            
            # Check for async query - need to poll for results
            query_id = query_response.get('query_id')
            async_result_link = query_response.get('async_result_link')
            
            if query_id and async_result_link:
                print(f"      [DEBUG] Async query created, ID: {query_id}")
                print(f"      [DEBUG] Polling results from: {async_result_link}")
                data = self._poll_async_results(query_id)
            else:
                # Direct data in response
                data = query_response.get('data', [])
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch data from Meta Audience Network: {str(e)}")
        
        # Initialize data structures
        ad_data = self._init_ad_data()
        platform_data = self._init_platform_data()
        
        total_revenue = 0.0
        total_impressions = 0
        
        # Parse response data
        if not data:
            print(f"      [DEBUG] Meta returned no data.")
        else:
            print(f"      [DEBUG] Meta got {len(data)} data entries")
        
        # Process results - Meta API returns each metric as a separate row
        # Example: {"metric": "fb_ad_network_revenue", "breakdowns": [...], "value": "26.59"}
        results = data if isinstance(data, list) else [data] if data else []
        
        for entry in results:
            try:
                # Handle nested results structure from query response
                if 'results' in entry:
                    for row in entry.get('results', []):
                        self._process_metric_row(row, ad_data, platform_data)
            except (TypeError, ValueError, KeyError) as e:
                print(f"      [DEBUG] Meta entry parse error: {str(e)}, entry: {str(entry)[:200]}")
                continue
        
        # Calculate totals from ad_data
        for ad_type in ad_data:
            total_revenue += ad_data[ad_type]['revenue']
            total_impressions += ad_data[ad_type]['impressions']
        
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
        
        print(f"      [INFO] Meta Total: ${result['revenue']:.2f} revenue, {result['impressions']:,} impressions")
        
        return result
    
    def _poll_async_results(self, query_id: str, max_attempts: int = 10) -> list:
        """
        Poll for async query results using adnetworkanalytics_results endpoint.
        
        Args:
            query_id: The async query ID
            max_attempts: Maximum polling attempts
            
        Returns:
            List of result data
        """
        import time
        
        # Use adnetworkanalytics_results endpoint
        results_url = f"{self.base_url}/{self.business_id}/adnetworkanalytics_results"
        params = {
            "access_token": self.access_token,
            "query_ids": json.dumps([query_id])
        }
        
        for attempt in range(max_attempts):
            print(f"      [DEBUG] Polling attempt {attempt + 1}/{max_attempts}...")
            
            response = requests.get(results_url, params=params, timeout=30)
            
            print(f"      [DEBUG] Poll response status: {response.status_code}")
            print(f"      [DEBUG] Poll response: {response.text[:500]}")
            
            if response.status_code != 200:
                print(f"      [DEBUG] Poll failed: {response.text[:200]}")
                time.sleep(2)
                continue
            
            data = response.json()
            results_data = data.get('data', [])
            
            if results_data:
                # Check if query is complete
                for item in results_data:
                    status = item.get('status', '')
                    print(f"      [DEBUG] Query status: {status}")
                    print(f"      [DEBUG] Full item: {json.dumps(item, indent=2)[:1000]}")
                    
                    if status == 'complete':
                        # Return the results
                        results = item.get('results', [])
                        print(f"      [DEBUG] Results count: {len(results) if results else 0}")
                        if results:
                            print(f"      [DEBUG] First result sample: {results[0] if results else 'empty'}")
                        return results
                    elif status in ['failed', 'error']:
                        raise Exception(f"Query failed: {item}")
            
            # Wait before next poll
            time.sleep(2)
        
        raise Exception("Query polling timed out")
    
    def _process_metric_row(self, row: dict, ad_data: dict, platform_data: dict):
        """
        Process a single metric row from Meta API.
        
        Meta API returns each metric as a separate row:
        {"metric": "fb_ad_network_revenue", "breakdowns": [...], "value": "26.59"}
        
        Args:
            row: Single row from API results
            ad_data: Ad type aggregated data
            platform_data: Platform aggregated data
        """
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
            
            # Only process revenue and impression metrics
            if metric == 'fb_ad_network_revenue':
                ad_data[ad_format]['revenue'] += value
                platform_data[platform]['ad_data'][ad_format]['revenue'] += value
                platform_data[platform]['revenue'] += value
            elif metric == 'fb_ad_network_imp':
                int_value = int(value)
                ad_data[ad_format]['impressions'] += int_value
                platform_data[platform]['ad_data'][ad_format]['impressions'] += int_value
                platform_data[platform]['impressions'] += int_value
            # Skip cpm - we calculate it ourselves
            
        except (TypeError, ValueError, KeyError) as e:
            print(f"      [DEBUG] Row process error: {str(e)}, row: {str(row)[:200]}")
    
    def get_network_name(self) -> str:
        """Return the network name."""
        return "Meta"

