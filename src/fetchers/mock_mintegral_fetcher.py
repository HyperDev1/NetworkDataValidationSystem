"""
Mock Mintegral data fetcher for testing purposes.
"""
from datetime import datetime
from typing import Dict, Any
from .base_fetcher import NetworkDataFetcher


class MockMintegralFetcher(NetworkDataFetcher):
    """Mock fetcher for Mintegral network data - for testing only."""
    
    def __init__(self, skey: str = None, secret: str = None, app_id: str = None):
        """Initialize Mock Mintegral fetcher."""
        print("  ⚠️  Using MOCK Mintegral data (real API not available)")
    
    def fetch_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Fetch mock data simulating Mintegral API with platform breakdown."""
        
        # Simulate data close to what Applovin shows for Mintegral (~$328)
        # Add small variance to create discrepancy
        android_ratio = 0.65
        ios_ratio = 0.35
        
        # Match approximately Applovin's Mintegral Bidding data with small variance
        total_revenue = 340.00  # Slightly different from Applovin's $328
        total_impressions = 24000
        
        ad_data = {
            'banner': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0},
            'interstitial': {'revenue': round(total_revenue * 0.6, 2), 'impressions': int(total_impressions * 0.5), 'ecpm': 0.0},
            'rewarded': {'revenue': round(total_revenue * 0.4, 2), 'impressions': int(total_impressions * 0.5), 'ecpm': 0.0}
        }
        
        # Calculate eCPM for ad types
        for key in ad_data:
            imp = ad_data[key]['impressions']
            rev = ad_data[key]['revenue']
            ad_data[key]['ecpm'] = round((rev / imp * 1000) if imp > 0 else 0.0, 2)
        
        total_ecpm = round((total_revenue / total_impressions * 1000) if total_impressions > 0 else 0.0, 2)
        
        platform_data = {
            'android': {
                'revenue': round(total_revenue * android_ratio, 2),
                'impressions': int(total_impressions * android_ratio),
                'ecpm': total_ecpm,
                'ad_data': {
                    'banner': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0},
                    'interstitial': {
                        'revenue': round(total_revenue * 0.6 * android_ratio, 2),
                        'impressions': int(total_impressions * 0.5 * android_ratio),
                        'ecpm': round(ad_data['interstitial']['ecpm'], 2)
                    },
                    'rewarded': {
                        'revenue': round(total_revenue * 0.4 * android_ratio, 2),
                        'impressions': int(total_impressions * 0.5 * android_ratio),
                        'ecpm': round(ad_data['rewarded']['ecpm'], 2)
                    }
                }
            },
            'ios': {
                'revenue': round(total_revenue * ios_ratio, 2),
                'impressions': int(total_impressions * ios_ratio),
                'ecpm': total_ecpm,
                'ad_data': {
                    'banner': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0},
                    'interstitial': {
                        'revenue': round(total_revenue * 0.6 * ios_ratio, 2),
                        'impressions': int(total_impressions * 0.5 * ios_ratio),
                        'ecpm': round(ad_data['interstitial']['ecpm'], 2)
                    },
                    'rewarded': {
                        'revenue': round(total_revenue * 0.4 * ios_ratio, 2),
                        'impressions': int(total_impressions * 0.5 * ios_ratio),
                        'ecpm': round(ad_data['rewarded']['ecpm'], 2)
                    }
                }
            }
        }
        
        return {
            'revenue': round(total_revenue, 2),
            'impressions': total_impressions,
            'ecpm': total_ecpm,
            'ad_data': ad_data,
            'platform_data': platform_data,
            'network': self.get_network_name(),
            'date_range': {
                'start': start_date.strftime("%Y-%m-%d"),
                'end': end_date.strftime("%Y-%m-%d")
            },
            'is_mock': True
        }
    
    def get_network_name(self) -> str:
        """Return the network name."""
        return "Mintegral"

