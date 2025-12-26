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
    
    # Ad type mapping
    AD_TYPE_MAP = {
        1: 'banner',
        2: 'interstitial',      # Native
        3: 'interstitial',      # Interstitial Video
        4: 'rewarded',          # Rewarded Video
        5: 'banner',            # Splash
        6: 'interstitial',      # Interactive
        7: 'banner',            # Banner
    }
    
    def __init__(self, skey: str, secret: str, app_id: str = None):
        """
        Initialize Mintegral fetcher.
        
        Args:
            skey: Mintegral API skey
            secret: Mintegral API secret
            app_id: Optional app ID to filter
        """
        self.skey = skey
        self.secret = secret
        self.app_id = app_id
        self.base_url = "https://api.mintegral.com/reporting/data"
    
    def _generate_sign(self, timestamp: str) -> str:
        """
        Generate MD5 signature for API authentication.
        
        Args:
            timestamp: Unix timestamp string
            
        Returns:
            MD5 hash signature
        """
        sign_str = f"{self.skey}{self.secret}{timestamp}"
        return hashlib.md5(sign_str.encode()).hexdigest()
    
    def fetch_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Fetch data from Mintegral Reporting API grouped by ad type.
        
        Args:
            start_date: Start date for data fetch
            end_date: End date for data fetch
            
        Returns:
            Dictionary containing revenue, impressions, and ecpm data by ad type
        """
        timestamp = str(int(time.time()))
        sign = self._generate_sign(timestamp)
        
        params = {
            "skey": self.skey,
            "timestamp": timestamp,
            "sign": sign,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "dimension": "ad_type",  # Group by ad type
        }
        
        # Add app_id filter if provided
        if self.app_id:
            params["app_id"] = self.app_id
        
        try:
            response = requests.get(
                self.base_url,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Check API response status
            if data.get('code') != 200:
                raise Exception(f"Mintegral API error: {data.get('msg', 'Unknown error')}")
            
            # Initialize data structure for each ad type
            ad_data = {
                'banner': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0},
                'interstitial': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0},
                'rewarded': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0}
            }
            
            # Platform buckets
            platform_data = {
                'android': {'ad_data': {k: {'revenue':0.0,'impressions':0,'ecpm':0.0} for k in ad_data}, 'revenue':0.0,'impressions':0,'ecpm':0.0},
                'ios': {'ad_data': {k: {'revenue':0.0,'impressions':0,'ecpm':0.0} for k in ad_data}, 'revenue':0.0,'impressions':0,'ecpm':0.0}
            }
            
            # Total values
            total_revenue = 0.0
            total_impressions = 0
            
            # Parse response data
            result_data = data.get('data', [])
            for row in result_data:
                revenue = float(row.get('revenue', row.get('est_revenue', 0)))
                impressions = int(row.get('impression', row.get('impressions', 0)))
                ad_type_id = row.get('ad_type', 0)
                # detect platform if available
                plat_val = str(row.get('os', row.get('platform', ''))).lower()
                if 'ios' in plat_val or 'iphone' in plat_val or 'ipad' in plat_val:
                    platform = 'ios'
                else:
                    platform = 'android'
                
                total_revenue += revenue
                total_impressions += impressions
                
                # Map ad type to our categories
                ad_category = self.AD_TYPE_MAP.get(ad_type_id, 'banner')
                ad_data[ad_category]['revenue'] += revenue
                ad_data[ad_category]['impressions'] += impressions
                
                # accumulate per-platform
                platform_data.setdefault(platform, {'ad_data': {k: {'revenue':0.0,'impressions':0,'ecpm':0.0} for k in ad_data}, 'revenue':0.0,'impressions':0,'ecpm':0.0})
                platform_data[platform]['ad_data'][ad_category]['revenue'] += revenue
                platform_data[platform]['ad_data'][ad_category]['impressions'] += impressions
                platform_data[platform]['revenue'] += revenue
                platform_data[platform]['impressions'] += impressions
            
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
        return "Mintegral"

