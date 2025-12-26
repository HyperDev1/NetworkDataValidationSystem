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
    
    def fetch_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Fetch data from Adjust API grouped by ad type.
        
        Args:
            start_date: Start date for data fetch
            end_date: End date for data fetch
            
        Returns:
            Dictionary containing revenue, impressions, and ecpm data by ad type
        """
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        # Adjust Dashboard Reports API payload - add ad_type dimension
        payload = {
            "date_period": f"{start_date.strftime('%Y-%m-%d')}:{end_date.strftime('%Y-%m-%d')}",
            "dimensions": ["app", "ad_type"],
            "metrics": ["revenue", "impressions"],
            "filters": {
                "app": [self.app_token]
            }
        }
        
        try:
            # Use POST for Dashboard Reports API
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Initialize data structure for each ad type
            ad_data = {
                'banner': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0},
                'interstitial': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0},
                'rewarded': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0}
            }
            
            # Total values
            total_revenue = 0.0
            total_impressions = 0
            
            # Parse rows
            rows = data.get('rows', data.get('data', []))
            
            for row in rows:
                revenue = float(row.get('revenue', row.get('ad_revenue', 0)))
                impressions = int(row.get('impressions', 0))
                ad_type = row.get('ad_type', '').lower()
                
                total_revenue += revenue
                total_impressions += impressions
                
                # Map to our categories
                if 'banner' in ad_type:
                    ad_data['banner']['revenue'] += revenue
                    ad_data['banner']['impressions'] += impressions
                elif 'interstitial' in ad_type or 'inter' in ad_type:
                    ad_data['interstitial']['revenue'] += revenue
                    ad_data['interstitial']['impressions'] += impressions
                elif 'rewarded' in ad_type or 'reward' in ad_type:
                    ad_data['rewarded']['revenue'] += revenue
                    ad_data['rewarded']['impressions'] += impressions
            
            # Calculate eCPM for each ad type
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
            raise Exception(f"Failed to fetch data from Adjust: {str(e)}")
    
    def get_network_name(self) -> str:
        """Return the network name."""
        return "Adjust"
