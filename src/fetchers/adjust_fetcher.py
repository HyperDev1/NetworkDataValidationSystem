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
        self.base_url = "https://api.adjust.com/kpis/v1"
    
    def fetch_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Fetch data from Adjust API.
        
        Args:
            start_date: Start date for data fetch
            end_date: End date for data fetch
            
        Returns:
            Dictionary containing revenue and impressions data
        """
        headers = {
            "Authorization": f"Bearer {self.api_token}"
        }
        
        params = {
            "app_token": self.app_token,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "kpis": "revenue,impressions",
            "grouping": "app"
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/{self.app_token}",
                headers=headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Parse Adjust API response
            revenue = 0.0
            impressions = 0
            
            if 'rows' in data and len(data['rows']) > 0:
                for row in data['rows']:
                    revenue += float(row.get('revenue', 0))
                    impressions += int(row.get('impressions', 0))
            
            return {
                'revenue': revenue,
                'impressions': impressions,
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
