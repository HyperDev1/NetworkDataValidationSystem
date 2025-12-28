"""
Google AdMob data fetcher implementation.
Uses AdMob API v1 for fetching monetization data.
API Docs: https://developers.google.com/admob/api/v1/reference/rest
"""
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from .base_fetcher import NetworkDataFetcher

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False


class AdmobFetcher(NetworkDataFetcher):
    """Fetcher for Google AdMob monetization data."""
    
    # AdMob API scopes
    SCOPES = ['https://www.googleapis.com/auth/admob.readonly']
    
    # Ad format mapping - AdMob format to our standard categories
    AD_FORMAT_MAP = {
        'BANNER': 'banner',
        'INTERSTITIAL': 'interstitial',
        'REWARDED': 'rewarded',
        'REWARDED_INTERSTITIAL': 'rewarded',
        'APP_OPEN': 'interstitial',
        'NATIVE': 'banner',
    }
    
    # Platform mapping
    PLATFORM_MAP = {
        'ANDROID': 'android',
        'IOS': 'ios',
    }
    
    def __init__(
        self,
        service_account_json_path: str,
        publisher_id: str,
        app_ids: Optional[str] = None
    ):
        """
        Initialize AdMob fetcher.
        
        Args:
            service_account_json_path: Path to Google Service Account JSON key file
            publisher_id: AdMob Publisher ID (format: pub-XXXXXXXXXXXXXXXX)
            app_ids: Optional comma-separated AdMob app IDs to filter
        """
        if not GOOGLE_API_AVAILABLE:
            raise ImportError(
                "Google API libraries not installed. "
                "Please install: pip install google-auth google-api-python-client"
            )
        
        self.service_account_json_path = service_account_json_path
        # Normalize publisher_id - remove 'pub-' prefix if present for account name
        self.publisher_id = publisher_id.replace('pub-', '') if publisher_id.startswith('pub-') else publisher_id
        self.app_ids = [a.strip() for a in app_ids.split(',') if a.strip()] if app_ids else []
        self.service = self._build_service()
        self.account_name = None  # Will be set during first fetch
    
    def _build_service(self):
        """Build AdMob API service with authentication."""
        if not os.path.exists(self.service_account_json_path):
            raise FileNotFoundError(
                f"Service account JSON file not found: {self.service_account_json_path}"
            )
        
        credentials = service_account.Credentials.from_service_account_file(
            self.service_account_json_path,
            scopes=self.SCOPES
        )
        
        return build('admob', 'v1', credentials=credentials)
    
    def _normalize_platform(self, platform: str) -> str:
        """Normalize platform name to standard format."""
        if not platform:
            return 'android'
        
        platform_upper = platform.upper().strip()
        return self.PLATFORM_MAP.get(platform_upper, 'android')
    
    def _normalize_ad_format(self, ad_format: str) -> str:
        """Normalize ad format to standard category."""
        if not ad_format:
            return 'interstitial'
        
        ad_format_upper = ad_format.upper().strip()
        return self.AD_FORMAT_MAP.get(ad_format_upper, 'interstitial')
    
    def _init_ad_data(self) -> Dict[str, Dict[str, Any]]:
        """Initialize empty ad data structure."""
        return {
            'banner': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0},
            'interstitial': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0},
            'rewarded': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0}
        }
    
    def _init_platform_data(self) -> Dict[str, Any]:
        """Initialize empty platform data structure."""
        return {
            'android': {
                'ad_data': self._init_ad_data(),
                'revenue': 0.0,
                'impressions': 0,
                'ecpm': 0.0
            },
            'ios': {
                'ad_data': self._init_ad_data(),
                'revenue': 0.0,
                'impressions': 0,
                'ecpm': 0.0
            }
        }
    
    def _calculate_ecpm(self, revenue: float, impressions: int) -> float:
        """Calculate eCPM from revenue and impressions."""
        if impressions <= 0:
            return 0.0
        return round((revenue / impressions) * 1000, 2)
    
    def _finalize_ecpm(self, data: Dict[str, Any]):
        """Calculate and update eCPM values in data structure."""
        for platform_key in ['android', 'ios']:
            platform = data['platform_data'][platform_key]
            
            # Calculate platform-level eCPM
            platform['ecpm'] = self._calculate_ecpm(
                platform['revenue'],
                platform['impressions']
            )
            
            # Calculate ad-type level eCPM
            for ad_type in ['banner', 'interstitial', 'rewarded']:
                ad_data = platform['ad_data'][ad_type]
                ad_data['ecpm'] = self._calculate_ecpm(
                    ad_data['revenue'],
                    ad_data['impressions']
                )
        
        # Calculate total eCPM
        data['ecpm'] = self._calculate_ecpm(data['revenue'], data['impressions'])
    
    def _get_account_name(self) -> str:
        """Get the AdMob account name. Lists accounts and finds matching one."""
        if self.account_name:
            return self.account_name
        
        try:
            # List all accounts accessible by this service account
            accounts_response = self.service.accounts().list().execute()
            accounts = accounts_response.get('account', [])
            
            print(f"      [INFO] Found {len(accounts)} AdMob account(s)")
            
            if not accounts:
                raise Exception(
                    "No AdMob accounts found. Please ensure the service account "
                    "has been invited to your AdMob account."
                )
            
            # Find matching account by publisher ID
            for account in accounts:
                account_name = account.get('name', '')
                publisher_id = account.get('publisherId', '')
                
                print(f"      [DEBUG] Account: {account_name}, Publisher: {publisher_id}")
                
                # Match by publisher ID (with or without pub- prefix)
                if self.publisher_id in publisher_id or publisher_id.replace('pub-', '') == self.publisher_id:
                    self.account_name = account_name
                    print(f"      [INFO] Using account: {account_name}")
                    return account_name
            
            # If no match, use first account
            self.account_name = accounts[0].get('name', '')
            print(f"      [WARN] Publisher ID not matched, using first account: {self.account_name}")
            return self.account_name
            
        except HttpError as e:
            print(f"      [ERROR] Failed to list accounts: {e.reason}")
            raise
    
    def fetch_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Fetch data from AdMob Mediation Report API.
        
        Args:
            start_date: Start date for data fetch
            end_date: End date for data fetch
            
        Returns:
            Dictionary containing revenue and impressions data by platform and ad type
        """
        print(f"      [INFO] Fetching AdMob data...")
        
        # Initialize result structure
        result = {
            'revenue': 0.0,
            'impressions': 0,
            'ecpm': 0.0,
            'network': self.get_network_name(),
            'platform_data': self._init_platform_data(),
            'date_range': {
                'start': start_date.strftime("%Y-%m-%d"),
                'end': end_date.strftime("%Y-%m-%d")
            }
        }
        
        try:
            # Build the mediation report request
            # Using Network Report for AdMob's own ad serving data
            request_body = {
                'reportSpec': {
                    'dateRange': {
                        'startDate': {
                            'year': start_date.year,
                            'month': start_date.month,
                            'day': start_date.day
                        },
                        'endDate': {
                            'year': end_date.year,
                            'month': end_date.month,
                            'day': end_date.day
                        }
                    },
                    'dimensions': ['DATE', 'APP', 'PLATFORM', 'FORMAT'],
                    'metrics': ['ESTIMATED_EARNINGS', 'IMPRESSIONS', 'IMPRESSION_RPM'],
                    'dimensionFilters': [],
                    'sortConditions': [
                        {'dimension': 'DATE', 'order': 'DESCENDING'}
                    ]
                }
            }
            
            # Add app filter if specified
            if self.app_ids:
                request_body['reportSpec']['dimensionFilters'].append({
                    'dimension': 'APP',
                    'matchesAny': {'values': self.app_ids}
                })
            
            # Get account name (will list accounts and find the correct one)
            account_name = self._get_account_name()
            
            report_request = self.service.accounts().networkReport().generate(
                parent=account_name,
                body=request_body
            )
            
            response = report_request.execute()
            
            # Process response rows
            rows = response.get('rows', []) if isinstance(response, dict) else []
            
            # Handle streaming response (list of dicts)
            if isinstance(response, list):
                rows = []
                for item in response:
                    if 'row' in item:
                        rows.append(item['row'])
            
            print(f"      [INFO] Retrieved {len(rows)} rows from AdMob")
            
            for row in rows:
                self._process_row(row, result)
            
            # Finalize eCPM calculations
            self._finalize_ecpm(result)
            
            print(f"      [INFO] AdMob Total: ${result['revenue']:.2f} revenue, {result['impressions']:,} impressions")
            
        except HttpError as e:
            print(f"      [ERROR] AdMob API error: {e.reason}")
            raise
        except Exception as e:
            print(f"      [ERROR] AdMob fetch error: {str(e)}")
            raise
        
        return result
    
    def _process_row(self, row: Dict[str, Any], result: Dict[str, Any]):
        """Process a single row from AdMob report response."""
        try:
            # Extract dimension values
            dimension_values = row.get('dimensionValues', {})
            metric_values = row.get('metricValues', {})
            
            # Get platform
            platform_value = dimension_values.get('PLATFORM', {}).get('value', '')
            platform = self._normalize_platform(platform_value)
            
            # Get ad format
            format_value = dimension_values.get('FORMAT', {}).get('value', '')
            ad_type = self._normalize_ad_format(format_value)
            
            # Get metrics - AdMob returns earnings in micros (1/1,000,000)
            earnings_micros = metric_values.get('ESTIMATED_EARNINGS', {}).get('microsValue', 0)
            revenue = float(earnings_micros) / 1_000_000 if earnings_micros else 0.0
            
            impressions = int(metric_values.get('IMPRESSIONS', {}).get('integerValue', 0))
            
            # Update platform data
            platform_data = result['platform_data'][platform]
            platform_data['revenue'] += revenue
            platform_data['impressions'] += impressions
            
            # Update ad type data
            ad_data = platform_data['ad_data'][ad_type]
            ad_data['revenue'] += revenue
            ad_data['impressions'] += impressions
            
            # Update totals
            result['revenue'] += revenue
            result['impressions'] += impressions
            
        except (KeyError, TypeError, ValueError) as e:
            print(f"      [WARN] Error processing row: {e}")
    
    def get_network_name(self) -> str:
        """Return the network name."""
        return "AdMob"

