"""
Mock Adjust data fetcher for testing purposes.
This fetcher returns simulated data when real Adjust API is not available.
"""
from datetime import datetime
from typing import Dict, Any
import random
from .base_fetcher import NetworkDataFetcher


class MockAdjustFetcher(NetworkDataFetcher):
    """Mock fetcher for Adjust network data - for testing only."""
    
    def __init__(self, api_token: str = None, app_token: str = None):
        """
        Initialize Mock Adjust fetcher.
        
        Args:
            api_token: Adjust API token (not used in mock)
            app_token: Adjust app token (not used in mock)
        """
        self.api_token = api_token
        self.app_token = app_token
        print("  ⚠️  Using MOCK Adjust data (real API not available)")
    
    def fetch_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Fetch mock data simulating Adjust API with ad type breakdown.
        
        Args:
            start_date: Start date for data fetch
            end_date: End date for data fetch
            
        Returns:
            Dictionary containing simulated revenue, impressions, and ecpm data by ad type
        """
        # Generate mock data with intentional discrepancy for testing
        # Banner data
        banner_revenue = 520.0 * 0.92  # ~478
        banner_impressions = 180000
        banner_ecpm = (banner_revenue / banner_impressions * 1000) if banner_impressions > 0 else 0.0
        
        # Interstitial data
        inter_revenue = 1480.0 * 0.94  # ~1391
        inter_impressions = 95000
        inter_ecpm = (inter_revenue / inter_impressions * 1000) if inter_impressions > 0 else 0.0
        
        # Rewarded data
        rewarded_revenue = 2000.0 * 0.93  # ~1860
        rewarded_impressions = 113800
        rewarded_ecpm = (rewarded_revenue / rewarded_impressions * 1000) if rewarded_impressions > 0 else 0.0
        
        # Total
        total_revenue = banner_revenue + inter_revenue + rewarded_revenue
        total_impressions = banner_impressions + inter_impressions + rewarded_impressions
        total_ecpm = (total_revenue / total_impressions * 1000) if total_impressions > 0 else 0.0
        
        ad_data = {
            'banner': {
                'revenue': round(banner_revenue, 2),
                'impressions': banner_impressions,
                'ecpm': round(banner_ecpm, 2)
            },
            'interstitial': {
                'revenue': round(inter_revenue, 2),
                'impressions': inter_impressions,
                'ecpm': round(inter_ecpm, 2)
            },
            'rewarded': {
                'revenue': round(rewarded_revenue, 2),
                'impressions': rewarded_impressions,
                'ecpm': round(rewarded_ecpm, 2)
            }
        }
        
        return {
            'revenue': round(total_revenue, 2),
            'impressions': total_impressions,
            'ecpm': round(total_ecpm, 2),
            'ad_data': ad_data,
            'network': self.get_network_name(),
            'date_range': {
                'start': start_date.strftime("%Y-%m-%d"),
                'end': end_date.strftime("%Y-%m-%d")
            },
            'is_mock': True  # Flag to indicate this is mock data
        }
    
    def get_network_name(self) -> str:
        """Return the network name."""
        return "Adjust (Mock)"

