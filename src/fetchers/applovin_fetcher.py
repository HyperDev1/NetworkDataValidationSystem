"""
AppLovin Max Network Comparison data fetcher implementation.
Fetches both MAX data and Network's own reported data for comparison.
Uses AppLovin Network Comparison Reporting API.
"""
import requests
from datetime import datetime
from typing import Dict, Any
from .base_fetcher import NetworkDataFetcher


class ApplovinFetcher(NetworkDataFetcher):
    """Fetcher for AppLovin Max Network Comparison data."""
    
    # Ad format mapping
    AD_FORMAT_NAMES = {
        'BANNER': 'Banner',
        'INTER': 'Interstitial', 
        'REWARDED': 'Rewarded'
    }
    
    # Network name mapping (Applovin network names to our standard names)
    NETWORK_NAME_MAP = {
        'APPLOVIN': 'Applovin Bidding',
        'APPLOVIN_EXCHANGE': 'Applovin Exchange',
        'APPLOVIN_NETWORK': 'Applovin Bidding',
        'ADMOB': 'Google Bidding',
        'FACEBOOK': 'Meta Bidding',
        'META_AUDIENCE_NETWORK': 'Meta Bidding',
        'FACEBOOK_NETWORK': 'Meta Bidding',
        'MINTEGRAL': 'Mintegral Bidding',
        'UNITY': 'Unity Bidding',
        'UNITY_ADS': 'Unity Bidding',
        'IRONSOURCE': 'Ironsource Bidding',
        'VUNGLE': 'Liftoff Bidding',
        'LIFTOFF': 'Liftoff Bidding',
        'LIFTOFF_MONETIZE': 'Liftoff Bidding',
        'CHARTBOOST': 'Chartboost Bidding',
        'INMOBI': 'Inmobi Bidding',
        'PANGLE': 'Pangle Bidding',
        'BYTEDANCE': 'Pangle Bidding',
        'TIKTOK': 'Pangle Bidding',
        'MOBILEFUSE': 'MobileFuse',
        'VERVE': 'Verve',
        'YANDEX': 'Yandex',
        'GOOGLE_AD_MANAGER': 'Google Ad Manager',
        'GOOGLE_AD_MANAGER_NETWORK': 'Google Ad Manager',
        'GOOGLE': 'Google Bidding',
        'HYPRMX': 'HyprMX',
        'MOLOCO': 'Moloco Bidding',
        'OGURY': 'Ogury',
        'SMAATO': 'Smaato',
        'SNAP': 'Snap',
        'FYBER': 'DT Exchange Bidding',
        'DT_EXCHANGE': 'DT Exchange Bidding',
        'BIDMACHINE': 'Bidmachine Bidding',
    }
    
    # Application name mapping (package name to display name)
    APP_NAME_MAP = {
        'com.hyperlab.clearandshoot': 'Clear And Shoot',
        'id1670670715': 'Clear And Shoot',
    }
    
    def __init__(self, api_key: str, applications: list = None):
        """
        Initialize Applovin fetcher.
        
        Args:
            api_key: Applovin API key
            applications: List of application configs with app_name, display_name, platform
        """
        self.api_key = api_key
        self.applications = applications or []
        self.base_url = "https://r.applovin.com/maxReport"
        
        # Build lookup maps from applications config
        self._app_name_to_display = {}
        self._allowed_app_names = set()
        
        for app in self.applications:
            app_name = app.get('app_name', '').strip()
            display = app.get('display_name', '')
            platform = app.get('platform', '')
            
            if app_name:
                # Store both original and lowercase for case-insensitive matching
                self._allowed_app_names.add(app_name.lower())
                self._app_name_to_display[app_name.lower()] = {
                    'display_name': display,
                    'platform': platform
                }
    
    def _detect_platform(self, row: Dict[str, Any]) -> str:
        """Detect platform (android/ios) from API row."""
        platform_val = str(row.get('platform', row.get('os', ''))).lower()
        
        if 'android' in platform_val:
            return 'Android'
        if 'ios' in platform_val or 'iphone' in platform_val or 'ipad' in platform_val:
            return 'iOS'
        
        # Fallback: detect from application field
        app = str(row.get('application', row.get('package_name', ''))).lower()
        if app.startswith('id') and app[2:].isdigit():
            return 'iOS'
        if 'ios' in app:
            return 'iOS'
        
        return 'Android'
    
    def _get_app_display_name(self, app_name: str, platform: str) -> str:
        """Get display name for application with platform."""
        app_name_lower = app_name.lower().strip()
        
        # First check config-based lookup
        if app_name_lower in self._app_name_to_display:
            config = self._app_name_to_display[app_name_lower]
            return f"{config['display_name']} ({config['platform']})"
        
        # Fallback: clean up the app name
        # Remove platform suffixes like "DRD", "IOS" 
        clean_name = app_name.replace(' DRD', '').replace(' IOS', '').replace(' ios', '').strip()
        
        return f"{clean_name} ({platform})"
    
    def _is_allowed_app(self, app_name: str) -> bool:
        """Check if app is in allowed list."""
        if not self._allowed_app_names:
            return True  # No filter, allow all
        return app_name.lower().strip() in self._allowed_app_names
    
    def _normalize_network_name(self, network: str) -> str:
        """Normalize network name to standard format."""
        if not network:
            return 'Unknown'
        
        # Remove common suffixes (case-insensitive)
        network_upper = network.upper()
        network_clean = network_upper.replace('_BIDDING', '').replace(' BIDDING', '')
        network_clean = network_clean.replace('_NETWORK', '').replace(' NETWORK', '')
        network_clean = network_clean.replace('_EXCHANGE', '').replace(' EXCHANGE', '')
        network_clean = network_clean.strip()
        
        # Direct mapping
        if network_clean in self.NETWORK_NAME_MAP:
            return self.NETWORK_NAME_MAP[network_clean]
        
        # Return cleaned title case
        return network_clean.replace('_', ' ').title()
    
    def _detect_ad_type(self, row: Dict[str, Any]) -> str:
        """Detect ad type from row data."""
        ad_format = (row.get('ad_format') or row.get('format') or row.get('format_name') or '')
        if isinstance(ad_format, str):
            ad_format_up = ad_format.upper()
        else:
            ad_format_up = str(ad_format).upper()
        
        if 'BANNER' in ad_format_up:
            return 'Banner'
        elif 'INTER' in ad_format_up or 'INTERSTITIAL' in ad_format_up:
            return 'Interstitial'
        elif 'REWARD' in ad_format_up or 'REWARDED' in ad_format_up:
            return 'Rewarded'
        else:
            return 'Other'
    
    def _calculate_delta(self, max_val: float, network_val: float) -> str:
        """Calculate delta percentage between MAX and Network values."""
        if max_val == 0 and network_val == 0:
            return "0.0%"
        elif max_val == 0:
            return "+∞%"
        
        delta = ((network_val - max_val) / max_val) * 100
        sign = "+" if delta > 0 else ""
        return f"{sign}{delta:.1f}%"
    
    def fetch_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Fetch Network Comparison data from AppLovin Max API.
        
        Returns:
            Dictionary containing comparison rows for each application/network/ad_type
        """
        print(f"      [INFO] Fetching Network Comparison data...")
        
        # First, try to fetch with Network Comparison columns
        # AppLovin Network Comparison uses: third_party_revenue, third_party_impressions, third_party_ecpm
        column_sets = [
            # Network Comparison columns (third party = network's own reported data)
            "day,application,platform,network,ad_format,estimated_revenue,impressions,ecpm,third_party_estimated_revenue,third_party_impressions,third_party_ecpm",
            # Alternative naming
            "day,application,platform,network,ad_format,estimated_revenue,impressions,ecpm,network_estimated_revenue,network_impressions",
            # Fallback to basic columns (MAX data only)
            "day,application,platform,network,ad_format,estimated_revenue,impressions,ecpm",
        ]
        
        data = None
        used_columns = None
        
        for columns in column_sets:
            params = {
                "api_key": self.api_key,
                "start": start_date.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d"),
                "columns": columns,
                "format": "json",
                "platform": "android,ios",
                "report_timezone": "UTC"
            }

            try:
                response = requests.get(self.base_url, params=params, timeout=30)
                print(f"      [INFO] API Status: {response.status_code} (columns: {columns[:50]}...)")
                
                if response.status_code >= 400:
                    print(f"      [WARN] Column set failed: {response.text[:100]}")
                    continue
                    
                data = response.json()
                if data and (data.get('results') or data.get('data') or data.get('rows')):
                    used_columns = columns
                    break
            except Exception as e:
                print(f"      [WARN] Request failed: {str(e)}")
                continue
        
        if data is None:
            raise Exception("Failed to fetch data from AppLovin Max API - all column sets failed")

        rows = data.get('results') or data.get('data') or data.get('rows') or []
        print(f"      [INFO] Retrieved {len(rows)} rows using columns: {used_columns[:60]}...")
        
        # Check if we have network comparison data
        has_network_data = used_columns and ('third_party' in used_columns or 'network_estimated' in used_columns)
        print(f"      [INFO] Network comparison data available: {has_network_data}")
        
        # Structure for aggregation: {(application_display, network, ad_type): comparison_data}
        aggregated = {}
        
        # Totals
        totals = {
            'max_revenue': 0.0,
            'network_revenue': 0.0,
            'max_impressions': 0,
            'network_impressions': 0
        }
        
        for row in rows:
            app_name = row.get('application', row.get('package_name', 'Unknown'))
            
            # Filter by allowed apps
            if not self._is_allowed_app(app_name):
                continue
            
            platform = self._detect_platform(row)
            application = self._get_app_display_name(app_name, platform)
            network = self._normalize_network_name(row.get('network', ''))
            ad_type = self._detect_ad_type(row)
            
            if network == 'Unknown' or ad_type == 'Other':
                continue
            
            # Parse values - MAX data
            try:
                max_revenue = float(row.get('estimated_revenue', 0) or 0)
                max_impressions = int(row.get('impressions', 0) or 0)
                
                # Network data - try different column names
                network_revenue = float(
                    row.get('third_party_estimated_revenue') or 
                    row.get('network_estimated_revenue') or 
                    row.get('estimated_revenue', 0) or 0
                )
                network_impressions = int(
                    row.get('third_party_impressions') or 
                    row.get('network_impressions') or 
                    row.get('impressions', 0) or 0
                )
            except (TypeError, ValueError):
                continue
            
            # Create key for aggregation
            key = (application, network, ad_type)
            
            if key not in aggregated:
                aggregated[key] = {
                    'application': application,
                    'network': network,
                    'ad_type': ad_type,
                    'max_impressions': 0,
                    'network_impressions': 0,
                    'max_revenue': 0.0,
                    'network_revenue': 0.0,
                }
            
            # Accumulate data
            aggregated[key]['max_revenue'] += max_revenue
            aggregated[key]['max_impressions'] += max_impressions
            aggregated[key]['network_revenue'] += network_revenue
            aggregated[key]['network_impressions'] += network_impressions
            
            # Accumulate totals
            totals['max_revenue'] += max_revenue
            totals['network_revenue'] += network_revenue
            totals['max_impressions'] += max_impressions
            totals['network_impressions'] += network_impressions
        
        # Convert to list and calculate eCPMs and deltas
        comparison_rows = []
        for key, cd in aggregated.items():
            # Calculate eCPMs
            cd['max_ecpm'] = round((cd['max_revenue'] / cd['max_impressions'] * 1000) if cd['max_impressions'] > 0 else 0, 2)
            cd['network_ecpm'] = round((cd['network_revenue'] / cd['network_impressions'] * 1000) if cd['network_impressions'] > 0 else 0, 2)
            
            # Round revenues
            cd['max_revenue'] = round(cd['max_revenue'], 2)
            cd['network_revenue'] = round(cd['network_revenue'], 2)
            
            # Calculate deltas
            cd['imp_delta'] = self._calculate_delta(cd['max_impressions'], cd['network_impressions'])
            cd['rev_delta'] = self._calculate_delta(cd['max_revenue'], cd['network_revenue'])
            cd['cpm_delta'] = self._calculate_delta(cd['max_ecpm'], cd['network_ecpm'])
            
            comparison_rows.append(cd)
        
        # Sort by application, then network, then ad_type
        comparison_rows.sort(key=lambda x: (x['application'], x['network'], x['ad_type']))
        
        return {
            'comparison_rows': comparison_rows,
            'totals': totals,
            'network': self.get_network_name(),
            'date_range': {
                'start': start_date.strftime("%Y-%m-%d"),
                'end': end_date.strftime("%Y-%m-%d")
            }
        }

    def get_network_name(self) -> str:
        """Return the network name."""
        return "AppLovin Max"

