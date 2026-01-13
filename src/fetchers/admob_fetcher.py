"""
Google AdMob data fetcher implementation.
Async version - uses Google API client (synchronous) wrapped for async interface.
Uses AdMob API v1 for fetching monetization data with OAuth 2.0.
API Docs: https://developers.google.com/admob/api/v1/reference/rest
"""
import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional

from .base_fetcher import NetworkDataFetcher, FetchResult
from ..enums import Platform, AdType, NetworkName

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    Credentials = None  # Type hint placeholder


logger = logging.getLogger(__name__)


class AdmobFetcher(NetworkDataFetcher):
    """
    Fetcher for Google AdMob monetization data using OAuth 2.0.
    
    OAuth 2.0 with Production mode:
    - Requires browser for initial authorization only
    - Token is cached and auto-refreshed (no expiration in Production mode)
    
    Note: Uses synchronous Google API client internally, wrapped for async interface.
    """
    
    # AdMob API scopes
    SCOPES = ['https://www.googleapis.com/auth/admob.readonly']
    
    # Ad format mapping - AdMob format to our standard enums
    AD_FORMAT_MAP = {
        'BANNER': AdType.BANNER,
        'INTERSTITIAL': AdType.INTERSTITIAL,
        'REWARDED': AdType.REWARDED,
        'REWARDED_INTERSTITIAL': AdType.REWARDED,
        'APP_OPEN': AdType.INTERSTITIAL,
        'NATIVE': AdType.BANNER,
    }
    
    # Platform mapping to enums
    PLATFORM_MAP = {
        'ANDROID': Platform.ANDROID,
        'IOS': Platform.IOS,
    }
    
    def __init__(
        self,
        publisher_id: str,
        app_ids: Optional[str] = None,
        oauth_credentials_path: Optional[str] = None,
        token_path: str = "credentials/admob_token.json",
        # Legacy parameter - ignored
        service_account_path: Optional[str] = None
    ):
        """
        Initialize AdMob fetcher with OAuth 2.0.
        
        Args:
            publisher_id: AdMob Publisher ID (format: pub-XXXXXXXXXXXXXXXX)
            app_ids: Optional comma-separated AdMob app IDs to filter
            oauth_credentials_path: Path to OAuth 2.0 client credentials JSON file
            token_path: Path to store/load OAuth token
        """
        super().__init__()
        
        if not GOOGLE_API_AVAILABLE:
            raise ImportError(
                "Google API libraries not installed. "
                "Please install: pip install google-auth google-auth-oauthlib google-api-python-client"
            )
        
        self.oauth_credentials_path = oauth_credentials_path
        self.token_path = token_path
        # Normalize publisher_id - remove 'pub-' prefix if present for account name
        self.publisher_id = publisher_id.replace('pub-', '') if publisher_id.startswith('pub-') else publisher_id
        self.app_ids = [a.strip() for a in app_ids.split(',') if a.strip()] if app_ids else []
        self.service = self._build_service()
        self.account_name = None  # Will be set during first fetch
    
    def _build_service(self):
        """Build AdMob API service with OAuth 2.0 authentication."""
        creds = self._authenticate_oauth()
        
        if not creds:
            raise ValueError(
                "OAuth authentication failed. "
                "Please provide valid oauth_credentials_path."
            )
        
        return build('admob', 'v1', credentials=creds)
    
    def _authenticate_oauth(self) -> Optional[Credentials]:
        """Authenticate using OAuth 2.0 (requires browser for initial auth)."""
        creds = None
        
        # Check if we have a saved token
        if os.path.exists(self.token_path):
            try:
                creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)
                logger.debug(f"Loaded existing OAuth token from {self.token_path}")
            except Exception as e:
                logger.warning(f"Failed to load token: {e}")
                creds = None
        
        # If no valid credentials, need to authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    logger.info("Refreshing expired OAuth token...")
                    creds.refresh(Request())
                    logger.info("Token refreshed successfully")
                except Exception as e:
                    logger.warning(f"Token refresh failed: {e}")
                    creds = None
            
            if not creds:
                # Need to do OAuth flow
                if not os.path.exists(self.oauth_credentials_path):
                    logger.warning(f"OAuth credentials file not found: {self.oauth_credentials_path}")
                    return None
                
                logger.info("Starting OAuth authorization flow...")
                logger.info("A browser window will open for authorization.")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.oauth_credentials_path,
                    self.SCOPES
                )
                # Try different ports if 8080 is in use
                for port in [8080, 8081, 8082, 8090, 9000]:
                    try:
                        creds = flow.run_local_server(port=port)
                        logger.info(f"OAuth authorization completed on port {port}")
                        break
                    except OSError as e:
                        if "Address already in use" in str(e):
                            logger.warning(f"Port {port} in use, trying next...")
                            continue
                        raise
                else:
                    raise RuntimeError("Could not find an available port for OAuth flow")
        
        # Save the credentials for next run
        if creds:
            self._save_token(creds)
        
        return creds
    
    def _save_token(self, creds: Credentials):
        """Save OAuth token to file for future use."""
        try:
            # Ensure directory exists
            token_dir = os.path.dirname(self.token_path)
            if token_dir and not os.path.exists(token_dir):
                os.makedirs(token_dir)
            
            with open(self.token_path, 'w') as token_file:
                token_file.write(creds.to_json())
            logger.debug(f"OAuth token saved to {self.token_path}")
        except Exception as e:
            logger.warning(f"Failed to save token: {e}")
    
    def _normalize_platform(self, platform: str) -> Platform:
        """Normalize platform name to Platform enum."""
        if not platform:
            return Platform.ANDROID
        
        platform_upper = platform.upper().strip()
        return self.PLATFORM_MAP.get(platform_upper, Platform.ANDROID)
    
    def _normalize_ad_format(self, ad_format: str) -> AdType:
        """Normalize ad format to AdType enum."""
        if not ad_format:
            return AdType.INTERSTITIAL
        
        ad_format_upper = ad_format.upper().strip()
        return self.AD_FORMAT_MAP.get(ad_format_upper, AdType.INTERSTITIAL)
    
    def _get_account_name(self) -> str:
        """Get the AdMob account name. Lists accounts and finds matching one."""
        if self.account_name:
            return self.account_name
        
        try:
            # List all accounts accessible by this service account
            accounts_response = self.service.accounts().list().execute()
            accounts = accounts_response.get('account', [])
            
            logger.debug(f"Found {len(accounts)} AdMob account(s)")
            
            if not accounts:
                raise Exception(
                    "No AdMob accounts found. Please ensure the service account "
                    "has been invited to your AdMob account."
                )
            
            # Find matching account by publisher ID
            for account in accounts:
                account_name = account.get('name', '')
                publisher_id = account.get('publisherId', '')
                
                logger.debug(f"Account: {account_name}, Publisher: {publisher_id}")
                
                # Match by publisher ID (with or without pub- prefix)
                if self.publisher_id in publisher_id or publisher_id.replace('pub-', '') == self.publisher_id:
                    self.account_name = account_name
                    logger.info(f"Using account: {account_name}")
                    return account_name
            
            # If no match, use first account
            self.account_name = accounts[0].get('name', '')
            logger.warning(f"Publisher ID not matched, using first account: {self.account_name}")
            return self.account_name
            
        except HttpError as e:
            logger.error(f"Failed to list accounts: {e.reason}")
            raise
    
    async def fetch_data(self, start_date: datetime, end_date: datetime) -> FetchResult:
        """
        Fetch data from AdMob Mediation Report API.
        
        Note: Uses synchronous Google API client internally, run in executor.
        
        Args:
            start_date: Start date for data fetch
            end_date: End date for data fetch
            
        Returns:
            FetchResult containing revenue and impressions data by platform and ad type
        """
        logger.debug("Fetching AdMob data...")
        
        # Initialize data structures using base class helpers
        ad_data = self._init_ad_data()
        platform_data = self._init_platform_data()
        
        # Daily breakdown data: {date_str: {platform: {ad_type: {revenue, impressions}}}}
        daily_data = {}
        
        total_revenue = 0.0
        total_impressions = 0
        
        try:
            # Build the mediation report request
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
            
            # Execute the synchronous Google API call in an executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.service.accounts().networkReport().generate(
                    parent=account_name,
                    body=request_body
                ).execute()
            )
            
            # Process response rows
            rows = response.get('rows', []) if isinstance(response, dict) else []
            
            # Handle streaming response (list of dicts)
            if isinstance(response, list):
                rows = []
                for item in response:
                    if 'row' in item:
                        rows.append(item['row'])
            
            logger.debug(f"Retrieved {len(rows)} rows from AdMob")
            
            for row in rows:
                revenue, impressions = self._process_row(row, ad_data, platform_data, daily_data)
                total_revenue += revenue
                total_impressions += impressions
            
            logger.info(f"AdMob Total: ${total_revenue:.2f} revenue, {total_impressions:,} impressions")
            
        except HttpError as e:
            logger.error(f"AdMob API error: {e.reason}")
            raise
        except Exception as e:
            logger.error(f"AdMob fetch error: {str(e)}")
            raise
        
        # Build result using base class helper
        result = self._build_result(start_date, end_date, total_revenue, total_impressions, ad_data, platform_data)
        
        # Add daily breakdown data for 7-day comparison
        result['daily_data'] = daily_data
        
        self._finalize_ecpm(result, ad_data, platform_data)
        
        return result
    
    def _process_row(self, row: Dict[str, Any], ad_data: Dict, platform_data: Dict, daily_data: Dict = None) -> tuple:
        """
        Process a single row from AdMob report response.
        
        Returns:
            Tuple of (revenue, impressions) added from this row
        """
        try:
            # Extract dimension values
            dimension_values = row.get('dimensionValues', {})
            metric_values = row.get('metricValues', {})
            
            # Get date from DATE dimension (format: {"value": "20260107"})
            date_value = dimension_values.get('DATE', {}).get('value', '')
            if date_value and len(date_value) == 8:
                # Convert YYYYMMDD to YYYY-MM-DD
                date_key = f"{date_value[:4]}-{date_value[4:6]}-{date_value[6:8]}"
            else:
                date_key = 'unknown'
            
            # Get platform as enum
            platform_value = dimension_values.get('PLATFORM', {}).get('value', '')
            platform = self._normalize_platform(platform_value)
            
            # Get ad format as enum
            format_value = dimension_values.get('FORMAT', {}).get('value', '')
            ad_type = self._normalize_ad_format(format_value)
            
            # Get metrics - AdMob returns earnings in micros (1/1,000,000)
            earnings_micros = metric_values.get('ESTIMATED_EARNINGS', {}).get('microsValue', 0)
            revenue = float(earnings_micros) / 1_000_000 if earnings_micros else 0.0
            
            impressions = int(metric_values.get('IMPRESSIONS', {}).get('integerValue', 0))
            
            # Accumulate using base class helper (note: parameter order is platform_data, ad_data)
            self._accumulate_metrics(platform_data, ad_data, platform, ad_type, revenue, impressions)
            
            # Accumulate daily breakdown if daily_data is provided
            if daily_data is not None:
                if date_key not in daily_data:
                    daily_data[date_key] = {}
                if platform.value not in daily_data[date_key]:
                    daily_data[date_key][platform.value] = {}
                if ad_type.value not in daily_data[date_key][platform.value]:
                    daily_data[date_key][platform.value][ad_type.value] = {'revenue': 0.0, 'impressions': 0}
                
                daily_data[date_key][platform.value][ad_type.value]['revenue'] += revenue
                daily_data[date_key][platform.value][ad_type.value]['impressions'] += impressions
            
            return (revenue, impressions)
            
        except (KeyError, TypeError, ValueError) as e:
            logger.warning(f"Error processing row: {e}")
            return (0.0, 0)
    
    def get_network_name(self) -> str:
        """Return the network name."""
        return NetworkName.ADMOB.display_name
    
    def get_network_enum(self) -> NetworkName:
        """Return the NetworkName enum."""
        return NetworkName.ADMOB

