"""
Mintegral data fetcher implementation.
"""
import requests
import hashlib
import time
from datetime import datetime
from typing import Dict, Any
from .base_fetcher import NetworkDataFetcher


class MintegralFetcher(NetworkDataFetcher):
    """Fetcher for Mintegral network data."""
    
    # Ad format mapping - Mintegral ad_format values to our categories
    # Note: Using only interstitial_video (not new_interstitial) to match MAX reporting
    AD_FORMAT_MAP = {
        'rewarded_video': 'rewarded',
        'interstitial_video': 'interstitial',
        'sdk_banner': 'banner',
    }
    
    def __init__(self, skey: str, secret: str, app_id: str = None):
        """
        Initialize Mintegral fetcher.
        
        Args:
            skey: Mintegral API skey
            secret: Mintegral API secret
            app_id: Optional app ID to filter (comma-separated for multiple apps)
        """
        self.skey = skey
        self.secret = secret
        self.app_id = app_id
        self.base_url = "https://api.mintegral.com/reporting/data"
    
    def _generate_sign(self, timestamp: int) -> str:
        """
        Generate MD5 signature for API authentication.
        sign = md5(SECRET + md5(time))
        """
        time_md5 = hashlib.md5(str(timestamp).encode()).hexdigest()
        return hashlib.md5((self.secret + time_md5).encode()).hexdigest()
    
    def _make_request(self, start_date: datetime, end_date: datetime, ad_format: str = None) -> Dict:
        """Make a single request to Mintegral API."""
        timestamp = int(time.time())
        sign = self._generate_sign(timestamp)
        
        params = {
            "skey": self.skey,
            "sign": sign,
            "time": timestamp,
            "start": start_date.strftime("%Y%m%d"),
            "end": end_date.strftime("%Y%m%d"),
            "group_by": "platform",
            "timezone": 0,
        }
        
        if self.app_id:
            params["app_id"] = self.app_id
        
        if ad_format:
            params["ad_format"] = ad_format
        
        response = requests.get(self.base_url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    
    def fetch_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Fetch data from Mintegral Reporting API grouped by ad type and platform.
        Makes separate requests for each ad_format since API doesn't return ad_format in response.
        """
        # Initialize data structures
        ad_data = {
            'banner': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0},
            'interstitial': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0},
            'rewarded': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0}
        }
        
        platform_data = {
            'android': {'ad_data': {k: {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0} for k in ad_data}, 'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0},
            'ios': {'ad_data': {k: {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0} for k in ad_data}, 'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0}
        }
        
        total_revenue = 0.0
        total_impressions = 0
        
        try:
            # Make separate request for each ad_format
            for mintegral_format, our_category in self.AD_FORMAT_MAP.items():
                try:
                    data = self._make_request(start_date, end_date, mintegral_format)
                    
                    if str(data.get('code', '')).lower() != 'ok':
                        print(f"      [DEBUG] Mintegral {mintegral_format}: {data.get('code')}")
                        continue
                    
                    rows = data.get('data', {}).get('lists', [])
                    
                    for row in rows:
                        revenue = float(row.get('est_revenue', 0) or 0)
                        impressions = int(row.get('impression', 0) or 0)
                        
                        # Detect platform
                        plat_val = str(row.get('platform', '')).lower()
                        platform = 'ios' if plat_val == 'ios' else 'android'
                        
                        # Accumulate totals
                        total_revenue += revenue
                        total_impressions += impressions
                        
                        # Accumulate by ad type
                        ad_data[our_category]['revenue'] += revenue
                        ad_data[our_category]['impressions'] += impressions
                        
                        # Accumulate per-platform
                        platform_data[platform]['ad_data'][our_category]['revenue'] += revenue
                        platform_data[platform]['ad_data'][our_category]['impressions'] += impressions
                        platform_data[platform]['revenue'] += revenue
                        platform_data[platform]['impressions'] += impressions
                        
                except Exception as e:
                    print(f"      [DEBUG] Mintegral {mintegral_format} error: {str(e)}")
                    continue
            
            # Calculate eCPM for each ad type
            for key in ad_data:
                imp = ad_data[key]['impressions']
                rev = ad_data[key]['revenue']
                ad_data[key]['ecpm'] = round((rev / imp * 1000) if imp > 0 else 0.0, 2)
                ad_data[key]['revenue'] = round(rev, 2)
            
            # Calculate per-platform eCPM
            for plat in platform_data:
                imp = platform_data[plat]['impressions']
                rev = platform_data[plat]['revenue']
                platform_data[plat]['ecpm'] = round((rev / imp * 1000) if imp > 0 else 0.0, 2)
                platform_data[plat]['revenue'] = round(rev, 2)
                for k in platform_data[plat]['ad_data']:
                    aimp = platform_data[plat]['ad_data'][k]['impressions']
                    arev = platform_data[plat]['ad_data'][k]['revenue']
                    platform_data[plat]['ad_data'][k]['ecpm'] = round((arev / aimp * 1000) if aimp > 0 else 0.0, 2)
                    platform_data[plat]['ad_data'][k]['revenue'] = round(arev, 2)
            
            # Calculate total eCPM
            total_ecpm = (total_revenue / total_impressions * 1000) if total_impressions > 0 else 0.0
            
            return {
                'revenue': round(total_revenue, 2),
                'impressions': total_impressions,
                'ecpm': round(total_ecpm, 2),
                'ad_data': ad_data,
                'platform_data': platform_data,
                'network': self.get_network_name(),
                'date_range': {
                    'start': start_date.strftime("%Y-%m-%d"),
                    'end': end_date.strftime("%Y-%m-%d")
                }
            }
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch data from Mintegral: {str(e)}")
    
    def get_network_name(self) -> str:
        """Return the network name."""
        return "Mintegral Bidding"

