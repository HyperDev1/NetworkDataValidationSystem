"""
Adjust data fetcher implementation.
"""
import requests
from datetime import datetime
from typing import Dict, Any
from .base_fetcher import NetworkDataFetcher


class AdjustFetcher(NetworkDataFetcher):
    """Fetcher for Adjust network data."""
    
    def __init__(self, api_token: str, app_token: str):
        """
        Initialize Adjust fetcher.
        
        Args:
            api_token: Adjust API token
            app_token: Adjust app token
        """
        self.api_token = api_token
        self.app_token = app_token
        # Using Adjust Dashboard Reports API (v2)
        self.base_url = "https://dash.adjust.com/control-center/reports-service/report"
    
    def _detect_platform(self, row: Dict[str, Any]) -> str:
        val = str(row.get('os', row.get('platform', row.get('os_name', '')))).lower()
        if 'android' in val:
            return 'android'
        if 'ios' in val or 'iphone' in val or 'ipad' in val:
            return 'ios'
        # default to android
        return 'android'
    
    def fetch_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Fetch data from Adjust API grouped by ad type and platform.
        """
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        # Adjust Dashboard Reports API payload
        payload = {
            "date_period": f"{start_date.strftime('%Y-%m-%d')}:{end_date.strftime('%Y-%m-%d')}",
            "dimensions": ["app"],
            "metrics": ["revenue", "impressions"],
            "filters": {
                "app": [self.app_token]
            }
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            # Initialize containers
            ad_data = {
                'banner': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0},
                'interstitial': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0},
                'rewarded': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0}
            }
            platform_data = {
                'android': {'ad_data': {k: {'revenue':0.0,'impressions':0,'ecpm':0.0} for k in ad_data}, 'revenue':0.0, 'impressions':0, 'ecpm':0.0},
                'ios': {'ad_data': {k: {'revenue':0.0,'impressions':0,'ecpm':0.0} for k in ad_data}, 'revenue':0.0, 'impressions':0, 'ecpm':0.0}
            }

            total_revenue = 0.0
            total_impressions = 0

            rows = data.get('rows', data.get('data', []))
            for row in rows:
                revenue = float(row.get('revenue', row.get('ad_revenue', 0)))
                impressions = int(row.get('impressions', 0))
                # try to detect ad type if present
                ad_type = str(row.get('ad_type', row.get('format', ''))).lower()
                platform = self._detect_platform(row)

                total_revenue += revenue
                total_impressions += impressions

                # map ad type to our keys
                if 'banner' in ad_type:
                    key = 'banner'
                elif 'reward' in ad_type:
                    key = 'rewarded'
                else:
                    key = 'interstitial'

                ad_data[key]['revenue'] += revenue
                ad_data[key]['impressions'] += impressions

                platform_data.setdefault(platform, {'ad_data': {k: {'revenue':0.0,'impressions':0,'ecpm':0.0} for k in ad_data}, 'revenue':0.0, 'impressions':0, 'ecpm':0.0})
                # if platform not recognized, map to android
                if platform not in platform_data:
                    platform = 'android'
                platform_data[platform]['ad_data'][key]['revenue'] += revenue
                platform_data[platform]['ad_data'][key]['impressions'] += impressions
                platform_data[platform]['revenue'] += revenue
                platform_data[platform]['impressions'] += impressions

            # calculate ecpm
            for k in ad_data:
                imp = ad_data[k]['impressions']
                rev = ad_data[k]['revenue']
                ad_data[k]['ecpm'] = round((rev / imp * 1000) if imp > 0 else 0.0, 2)
                ad_data[k]['revenue'] = round(rev, 2)

            for plat in platform_data:
                plat_imp = platform_data[plat]['impressions']
                plat_rev = platform_data[plat]['revenue']
                platform_data[plat]['ecpm'] = round((plat_rev / plat_imp * 1000) if plat_imp > 0 else 0.0, 2)
                for k in platform_data[plat]['ad_data']:
                    aimp = platform_data[plat]['ad_data'][k]['impressions']
                    arev = platform_data[plat]['ad_data'][k]['revenue']
                    platform_data[plat]['ad_data'][k]['ecpm'] = round((arev / aimp * 1000) if aimp > 0 else 0.0, 2)
                    platform_data[plat]['ad_data'][k]['revenue'] = round(arev, 2)

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
            raise Exception(f"Failed to fetch data from Adjust: {str(e)}")

    def get_network_name(self) -> str:
        """Return the network name."""
        return "Adjust"
