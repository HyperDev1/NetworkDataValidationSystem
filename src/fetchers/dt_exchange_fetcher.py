"""
DT Exchange (Digital Turbine) Reporting API data fetcher implementation.
Async version using aiohttp with retry support.
API Docs: https://developer.digitalturbine.com/hc/en-us/articles/8101286018717-DT-Exchange-Reporting-API
"""
import asyncio
import csv
import io
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from .base_fetcher import NetworkDataFetcher, FetchResult
from ..enums import Platform, AdType, NetworkName
from ..utils import TokenCache


logger = logging.getLogger(__name__)


class DTExchangeFetcher(NetworkDataFetcher):
    """Fetcher for DT Exchange (Digital Turbine) monetization data."""
    
    # DT Exchange API endpoints
    BASE_URL = "https://reporting.fyber.com"
    AUTH_ENDPOINT = "/auth/v1/token"
    REPORT_ENDPOINT = "/api/v1/report"
    
    # Polling configuration
    POLL_INTERVAL_SECONDS = 5  # Initial poll interval
    POLL_MAX_WAIT_SECONDS = 300  # 5 minutes timeout
    
    # Token cache key
    TOKEN_CACHE_KEY = "dt_exchange"
    TOKEN_EXPIRES_IN = 3540  # 59 minutes (actual is 60, with buffer)
    
    # Platform mapping - from API response "Device OS" field
    PLATFORM_MAP = {
        'android': Platform.ANDROID,
        'Android': Platform.ANDROID,
        'ios': Platform.IOS,
        'iOS': Platform.IOS,
    }
    
    # Ad type mapping - from API response "Placement Type" field
    AD_TYPE_MAP = {
        'banner': AdType.BANNER,
        'Banner': AdType.BANNER,
        'interstitial': AdType.INTERSTITIAL,
        'Interstitial': AdType.INTERSTITIAL,
        'rewarded': AdType.REWARDED,
        'Rewarded': AdType.REWARDED,
    }
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        source: str = "mediation",
        app_ids: Optional[str] = None,
    ):
        """
        Initialize DT Exchange fetcher.
        
        Args:
            client_id: OAuth 2.0 Client ID from DT Exchange dashboard
            client_secret: OAuth 2.0 Client Secret from DT Exchange dashboard
            source: Report source, default "mediation" for DT Exchange
            app_ids: Optional comma-separated Fyber App IDs to filter
        """
        super().__init__()
        self.client_id = client_id
        self.client_secret = client_secret
        self.source = source
        self.app_ids = app_ids
        self._token_cache = TokenCache()
    
    async def _get_access_token(self) -> str:
        """
        Get OAuth 2.0 access token from cache or auth endpoint.
        
        Returns:
            Valid access token string
        """
        # Check cache first
        cached = self._token_cache.get_token(self.TOKEN_CACHE_KEY)
        if cached:
            logger.debug("Using cached DT Exchange token")
            return cached['token']
        
        url = f"{self.BASE_URL}{self.AUTH_ENDPOINT}"
        
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        
        try:
            data = await self._post_json(url, json=payload)
        except Exception as e:
            error_str = str(e)
            if '400' in error_str:
                raise Exception(
                    "DT Exchange authentication failed (400 Bad Request). "
                    "Please check your client_id and client_secret in config.yaml."
                )
            if '401' in error_str:
                raise Exception(
                    "DT Exchange authentication failed (401 Unauthorized). "
                    "Invalid client credentials."
                )
            if '500' in error_str:
                raise Exception(
                    "DT Exchange authentication failed (500 Internal Server Error). "
                    "Please try again later."
                )
            raise Exception(f"DT Exchange auth error: {error_str}")
        
        token = data.get("accessToken")
        if not token:
            raise Exception("No accessToken in DT Exchange auth response")
        
        # Cache the token
        self._token_cache.save_token(
            self.TOKEN_CACHE_KEY,
            token,
            expires_in=self.TOKEN_EXPIRES_IN
        )
        
        return token
    
    async def _request_report(
        self,
        start_date: str,
        end_date: str,
    ) -> str:
        """
        Request a report from DT Exchange API.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            URL to poll for the CSV report
        """
        token = await self._get_access_token()
        
        url = f"{self.BASE_URL}{self.REPORT_ENDPOINT}?format=csv"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        # Build report request payload
        payload = {
            "source": self.source,
            "dateRange": {
                "start": start_date,
                "end": end_date,
            },
            "metrics": [
                "Impressions",
                "Clicks",
                "Revenue (USD)",
            ],
            "splits": [
                "Date",
                "Device OS",
                "Placement Type",
            ],
            "filters": [],
        }
        
        # Add app ID filter if specified
        if self.app_ids:
            app_id_list = [aid.strip() for aid in self.app_ids.split(",") if aid.strip()]
            if app_id_list:
                payload["filters"].append({
                    "dimension": "Fyber App ID",
                    "values": app_id_list,
                })
        
        try:
            data = await self._post_json(url, headers=headers, json=payload)
        except Exception as e:
            error_str = str(e)
            if '401' in error_str:
                # Token might have expired, clear cache and retry once
                self._token_cache.delete_token(self.TOKEN_CACHE_KEY)
                token = await self._get_access_token()
                headers['Authorization'] = f'Bearer {token}'
                data = await self._post_json(url, headers=headers, json=payload)
            else:
                raise Exception(f"DT Exchange report error: {error_str}")
        
        report_url = data.get("url")
        if not report_url:
            raise Exception("No report URL in DT Exchange response")
        
        return report_url
    
    async def _poll_report_url(self, report_url: str) -> str:
        """
        Poll the report URL until CSV data is ready.
        
        Args:
            report_url: S3 URL to poll for CSV data
            
        Returns:
            CSV content as string
        """
        import aiohttp
        
        start_time = asyncio.get_event_loop().time()
        poll_interval = self.POLL_INTERVAL_SECONDS
        
        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > self.POLL_MAX_WAIT_SECONDS:
                raise Exception(
                    f"DT Exchange report polling timeout after {self.POLL_MAX_WAIT_SECONDS} seconds. "
                    "The report may still be generating. Please try again later."
                )
            
            try:
                session = await self._get_session()
                async with session.get(report_url, timeout=aiohttp.ClientTimeout(total=60)) as response:
                    if response.status == 200:
                        content = await response.text()
                        if content and len(content) > 0:
                            return content
                    
                    if response.status == 404:
                        # Report not ready yet, continue polling
                        pass
                    elif response.status >= 400:
                        raise Exception(
                            f"DT Exchange report download failed: {response.status}"
                        )
                        
            except asyncio.TimeoutError:
                # Network timeout, continue polling
                pass
            except Exception as e:
                if 'download failed' in str(e):
                    raise
                # Other errors, continue polling
                pass
            
            # Exponential backoff with max interval
            await asyncio.sleep(poll_interval)
            poll_interval = min(poll_interval * 1.5, 30)
    
    def _parse_csv_response(self, csv_content: str) -> List[Dict[str, Any]]:
        """
        Parse CSV response into list of dictionaries.
        
        Args:
            csv_content: Raw CSV string from report
            
        Returns:
            List of row dictionaries
        """
        rows = []
        
        try:
            reader = csv.DictReader(io.StringIO(csv_content))
            for row in reader:
                rows.append(row)
        except Exception as e:
            raise Exception(f"Failed to parse DT Exchange CSV: {e}")
        
        return rows
    
    def _process_report_data(
        self, 
        report_data: List[Dict[str, Any]],
        ad_data: Dict,
        platform_data: Dict,
        daily_data: Dict
    ) -> tuple:
        """
        Process report data and aggregate by platform with daily breakdown.
        
        Args:
            report_data: List of report rows from CSV
            ad_data: Ad data dict to populate
            platform_data: Platform data dict to populate
            daily_data: Daily breakdown dict to populate
            
        Returns:
            Tuple of (total_revenue, total_impressions)
        """
        total_revenue = 0.0
        total_impressions = 0
        
        for row in report_data:
            if not isinstance(row, dict):
                continue
            
            # Get date from "Date" column (format: YYYY-MM-DD)
            date_key = row.get('Date', '')
            if not date_key:
                date_key = 'unknown'
            
            # Get platform from "Device OS" column
            platform_raw = row.get('Device OS', '')
            platform = self._normalize_platform(platform_raw)
            
            # Get ad type from "Placement Type" column
            ad_type_raw = row.get('Placement Type', '')
            ad_type = self._normalize_ad_type(ad_type_raw)
            
            # Extract metrics
            rev_str = row.get('Revenue (USD)', '0')
            rev = float(rev_str) if rev_str else 0.0
            
            imps_str = row.get('Impressions', '0')
            imps = int(float(imps_str)) if imps_str else 0
            
            # Accumulate totals
            total_revenue += rev
            total_impressions += imps
            
            # Use base class helper to accumulate metrics
            self._accumulate_metrics(
                platform_data, ad_data,
                platform, ad_type,
                rev, imps
            )
            
            # Accumulate daily breakdown
            if date_key not in daily_data:
                daily_data[date_key] = {}
            if platform.value not in daily_data[date_key]:
                daily_data[date_key][platform.value] = {}
            if ad_type.value not in daily_data[date_key][platform.value]:
                daily_data[date_key][platform.value][ad_type.value] = {'revenue': 0.0, 'impressions': 0}
            
            daily_data[date_key][platform.value][ad_type.value]['revenue'] += rev
            daily_data[date_key][platform.value][ad_type.value]['impressions'] += imps
        
        return total_revenue, total_impressions
    
    async def fetch_data(self, start_date: datetime, end_date: datetime) -> FetchResult:
        """
        Fetch revenue and impression data for the given date range.
        
        Args:
            start_date: Start date for data fetch
            end_date: End date for data fetch
            
        Returns:
            FetchResult containing revenue and impressions data with daily breakdown
        """
        # Format dates as YYYY-MM-DD
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        # Initialize data structures using base class helpers
        ad_data = self._init_ad_data()
        platform_data = self._init_platform_data()
        
        # Daily breakdown data: {date_str: {platform: {ad_type: {revenue, impressions}}}}
        daily_data = {}
        
        # Request async report
        report_url = await self._request_report(start_str, end_str)
        
        # Poll for CSV data
        csv_content = await self._poll_report_url(report_url)
        
        # Parse CSV
        report_data = self._parse_csv_response(csv_content)
        
        # Process and aggregate data
        total_revenue, total_impressions = self._process_report_data(
            report_data, ad_data, platform_data, daily_data
        )
        
        # Build result using base class helper
        result = self._build_result(
            start_date, end_date,
            revenue=total_revenue,
            impressions=total_impressions,
            ad_data=ad_data,
            platform_data=platform_data
        )
        
        # Add daily breakdown data for 7-day comparison
        result['daily_data'] = daily_data
        
        # Finalize eCPM calculations
        self._finalize_ecpm(result, ad_data, platform_data)
        
        return result
    
    def get_network_name(self) -> str:
        """Return the name of the network."""
        return NetworkName.DT_EXCHANGE.display_name
    
    def get_network_enum(self) -> NetworkName:
        """Return the NetworkName enum."""
        return NetworkName.DT_EXCHANGE
