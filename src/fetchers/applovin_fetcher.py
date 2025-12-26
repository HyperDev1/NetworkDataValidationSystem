"""
Applovin Max data fetcher implementation.
"""
import requests
from datetime import datetime
from typing import Dict, Any
from .base_fetcher import NetworkDataFetcher


class ApplovinFetcher(NetworkDataFetcher):
    """Fetcher for Applovin Max network data."""
    
    # Ad format mapping
    AD_FORMATS = ['BANNER', 'INTER', 'REWARDED']
    AD_FORMAT_NAMES = {
        'BANNER': 'Banner',
        'INTER': 'Interstitial', 
        'REWARDED': 'Rewarded'
    }
    
    def __init__(self, api_key: str, package_name: str):
        """
        Initialize Applovin fetcher.
        
        Args:
            api_key: Applovin API key
            package_name: App package name
        """
        self.api_key = api_key
        self.package_name = package_name
        self.base_url = "https://r.applovin.com/maxReport"
    
    def fetch_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Fetch data from Applovin Max API grouped by ad format.
        
        Args:
            start_date: Start date for data fetch
            end_date: End date for data fetch
            
        Returns:
            Dictionary containing revenue, impressions, and ecpm data by ad format
        """
        params = {
            "api_key": self.api_key,
            "start": start_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d"),
            "columns": "day,package_name,ad_format,estimated_revenue,impressions",
            "format": "json",
            "filter_package_name": self.package_name
        }
        
        try:
            response = requests.get(
                self.base_url,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Initialize data structure for each ad format
            ad_data = {
                'banner': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0},
                'interstitial': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0},
                'rewarded': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0}
            }
            
            # Total values
            total_revenue = 0.0
            total_impressions = 0
            
            if 'results' in data:
                for row in data['results']:
                    revenue = float(row.get('estimated_revenue', 0))
                    impressions = int(row.get('impressions', 0))
                    ad_format = row.get('ad_format', '').upper()
                    
                    total_revenue += revenue
                    total_impressions += impressions
                    
                    # Map to our categories
                    if ad_format == 'BANNER':
                        ad_data['banner']['revenue'] += revenue
                        ad_data['banner']['impressions'] += impressions
                    elif ad_format == 'INTER':
                        ad_data['interstitial']['revenue'] += revenue
                        ad_data['interstitial']['impressions'] += impressions
                    elif ad_format == 'REWARDED':
                        ad_data['rewarded']['revenue'] += revenue
                        ad_data['rewarded']['impressions'] += impressions
            
            # Calculate eCPM for each ad format
            for key in ad_data:
                imp = ad_data[key]['impressions']
                rev = ad_data[key]['revenue']
                ad_data[key]['ecpm'] = round((rev / imp * 1000) if imp > 0 else 0.0, 2)
                ad_data[key]['revenue'] = round(rev, 2)
            
            # Calculate total eCPM
            total_ecpm = (total_revenue / total_impressions * 1000) if total_impressions > 0 else 0.0
            
            return {
                'revenue': round(total_revenue, 2),
                'impressions': total_impressions,
                'ecpm': round(total_ecpm, 2),
                'ad_data': ad_data,
                'network': self.get_network_name(),
                'date_range': {
                    'start': start_date.strftime("%Y-%m-%d"),
                    'end': end_date.strftime("%Y-%m-%d")
                }
            }
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch data from Applovin Max: {str(e)}")
    
    def get_network_name(self) -> str:
        """Return the network name."""
        return "Applovin Max"
