"""
Applovin Max data fetcher implementation.
"""
import requests
from datetime import datetime
from typing import Dict, Any
from .base_fetcher import NetworkDataFetcher


class ApplovinFetcher(NetworkDataFetcher):
    """Fetcher for Applovin Max network data."""
    
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
        Fetch data from Applovin Max API.
        
        Args:
            start_date: Start date for data fetch
            end_date: End date for data fetch
            
        Returns:
            Dictionary containing revenue and impressions data
        """
        params = {
            "api_key": self.api_key,
            "start": start_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d"),
            "columns": "day,package_name,estimated_revenue,impressions",
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
            
            # Parse Applovin API response
            revenue = 0.0
            impressions = 0
            
            if 'results' in data:
                for row in data['results']:
                    revenue += float(row.get('estimated_revenue', 0))
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
            raise Exception(f"Failed to fetch data from Applovin Max: {str(e)}")
    
    def get_network_name(self) -> str:
        """Return the network name."""
        return "Applovin Max"
