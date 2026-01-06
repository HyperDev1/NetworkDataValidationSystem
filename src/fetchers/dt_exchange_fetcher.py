"""
DT Exchange (Digital Turbine) Reporting API data fetcher implementation.
API Docs: https://developer.digitalturbine.com/hc/en-us/articles/8101286018717-DT-Exchange-Reporting-API
"""
import requests
import time
import csv
import io
from datetime import datetime
from typing import Dict, Any, Optional, List
from .base_fetcher import NetworkDataFetcher


class DTExchangeFetcher(NetworkDataFetcher):
    """Fetcher for DT Exchange (Digital Turbine) monetization data."""
    
    # DT Exchange API endpoints
    BASE_URL = "https://reporting.fyber.com"
    AUTH_ENDPOINT = "/auth/v1/token"
    REPORT_ENDPOINT = "/api/v1/report"
    
    # Polling configuration
    POLL_INTERVAL_SECONDS = 5  # Initial poll interval
    POLL_MAX_WAIT_SECONDS = 300  # 5 minutes timeout
    
    # Platform mapping - from API response "Device OS" field
    PLATFORM_MAP = {
        'android': 'android',
        'Android': 'android',
        'ios': 'ios',
        'iOS': 'ios',
    }
    
    # Ad type mapping - from API response "Placement Type" field
    AD_TYPE_MAP = {
        'banner': 'banner',
        'Banner': 'banner',
        'interstitial': 'interstitial',
        'Interstitial': 'interstitial',
        'rewarded': 'rewarded',
        'Rewarded': 'rewarded',
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
        self.client_id = client_id
        self.client_secret = client_secret
        self.source = source
        self.app_ids = app_ids
        
        # Token caching
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[float] = None
    
    def _get_access_token(self) -> str:
        """
        Get OAuth 2.0 access token, refreshing if expired.
        
        Returns:
            Valid access token string
            
        Raises:
            Exception: If authentication fails
        """
        # Check if we have a valid cached token
        if self._access_token and self._token_expires_at:
            # Refresh 60 seconds before expiry
            if time.time() < self._token_expires_at - 60:
                return self._access_token
        
        url = f"{self.BASE_URL}{self.AUTH_ENDPOINT}"
        
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 400:
            raise Exception(
                "DT Exchange authentication failed (400 Bad Request). "
                "Please check your client_id and client_secret in config.yaml."
            )
        
        if response.status_code == 401:
            raise Exception(
                "DT Exchange authentication failed (401 Unauthorized). "
                "Invalid client credentials. Please verify your client_id and client_secret."
            )
        
        if response.status_code == 500:
            raise Exception(
                "DT Exchange authentication failed (500 Internal Server Error). "
                "Please try again later."
            )
        
        if response.status_code != 200:
            error_msg = f"DT Exchange auth error: {response.status_code}"
            try:
                error_msg += f" - {response.text[:500]}"
            except:
                pass
            raise Exception(error_msg)
        
        try:
            data = response.json()
            self._access_token = data.get("accessToken")
            expires_in = data.get("expiresIn", 3600)
            self._token_expires_at = time.time() + expires_in
            
            if not self._access_token:
                raise Exception("No accessToken in DT Exchange auth response")
            
            return self._access_token
        except Exception as e:
            if "DT Exchange" in str(e):
                raise
            raise Exception(f"Failed to parse DT Exchange auth response: {e}")
    
    def _request_report(
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
        token = self._get_access_token()
        
        url = f"{self.BASE_URL}{self.REPORT_ENDPOINT}?format=csv"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        # Build report request payload
        # Supported splits for mediation source: Device OS, Placement Type, Fyber App ID, Country
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
        
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=60
        )
        
        if response.status_code == 401:
            # Token might have expired, clear cache and retry once
            self._access_token = None
            self._token_expires_at = None
            raise Exception(
                "DT Exchange report request failed (401). Token may have expired. "
                "Please retry."
            )
        
        if response.status_code != 200:
            error_msg = f"DT Exchange report error: {response.status_code}"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_msg += f" - {error_data['error']}"
                if "message" in error_data:
                    error_msg += f" - {error_data['message']}"
            except:
                error_msg += f" - {response.text[:500]}"
            raise Exception(error_msg)
        
        try:
            data = response.json()
            report_url = data.get("url")
            
            if not report_url:
                raise Exception("No report URL in DT Exchange response")
            
            return report_url
        except Exception as e:
            if "DT Exchange" in str(e):
                raise
            raise Exception(f"Failed to parse DT Exchange report response: {e}")
    
    def _poll_report_url(self, report_url: str) -> str:
        """
        Poll the report URL until CSV data is ready.
        
        Args:
            report_url: S3 URL to poll for CSV data
            
        Returns:
            CSV content as string
        """
        start_time = time.time()
        poll_interval = self.POLL_INTERVAL_SECONDS
        
        while True:
            elapsed = time.time() - start_time
            if elapsed > self.POLL_MAX_WAIT_SECONDS:
                raise Exception(
                    f"DT Exchange report polling timeout after {self.POLL_MAX_WAIT_SECONDS} seconds. "
                    "The report may still be generating. Please try again later."
                )
            
            try:
                response = requests.get(report_url, timeout=60)
                
                if response.status_code == 200:
                    # Check if content is actually CSV (not empty or error page)
                    content = response.text
                    if content and len(content) > 0:
                        # Simple check: CSV should start with headers
                        return content
                
                if response.status_code == 404:
                    # Report not ready yet, continue polling
                    pass
                elif response.status_code >= 400:
                    raise Exception(
                        f"DT Exchange report download failed: {response.status_code}"
                    )
                    
            except requests.exceptions.RequestException as e:
                # Network error, continue polling
                pass
            
            # Exponential backoff with max interval
            time.sleep(poll_interval)
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
    
    def _create_empty_platform_data(self) -> Dict[str, Any]:
        """Create empty platform data structure."""
        return {
            'revenue': 0.0,
            'impressions': 0,
            'ecpm': 0.0,
            'clicks': 0,
            'ad_data': {
                'banner': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0, 'clicks': 0},
                'interstitial': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0, 'clicks': 0},
                'rewarded': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0, 'clicks': 0},
            }
        }
    
    def _process_report_data(self, report_data: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Process report data and aggregate by platform.
        
        Args:
            report_data: List of report rows from CSV
            
        Returns:
            Dictionary with platform_data structure
        """
        platform_data = {
            'android': self._create_empty_platform_data(),
            'ios': self._create_empty_platform_data(),
        }
        
        for row in report_data:
            if not isinstance(row, dict):
                continue
            
            # Get platform from "Device OS" column
            platform_raw = row.get('Device OS', '')
            platform = self.PLATFORM_MAP.get(platform_raw)
            
            if platform is None:
                continue
            
            # Get ad type from "Placement Type" column
            ad_type_raw = row.get('Placement Type', '')
            ad_type = self.AD_TYPE_MAP.get(ad_type_raw, 'interstitial')
            
            # Extract metrics
            # Revenue
            rev_str = row.get('Revenue (USD)', '0')
            rev = float(rev_str) if rev_str else 0.0
            
            # Impressions
            imps_str = row.get('Impressions', '0')
            imps = int(float(imps_str)) if imps_str else 0
            
            # Clicks
            clicks_str = row.get('Clicks', '0')
            clks = int(float(clicks_str)) if clicks_str else 0
            
            # Aggregate platform totals
            platform_data[platform]['revenue'] += rev
            platform_data[platform]['impressions'] += imps
            platform_data[platform]['clicks'] += clks
            
            # Aggregate by ad type
            platform_data[platform]['ad_data'][ad_type]['revenue'] += rev
            platform_data[platform]['ad_data'][ad_type]['impressions'] += imps
            platform_data[platform]['ad_data'][ad_type]['clicks'] += clks
        
        # Calculate eCPMs
        for platform in ['android', 'ios']:
            p_data = platform_data[platform]
            if p_data['impressions'] > 0:
                p_data['ecpm'] = (p_data['revenue'] / p_data['impressions']) * 1000
            
            for ad_type in ['banner', 'interstitial', 'rewarded']:
                ad_data = p_data['ad_data'][ad_type]
                if ad_data['impressions'] > 0:
                    ad_data['ecpm'] = (ad_data['revenue'] / ad_data['impressions']) * 1000
        
        return platform_data
    
    def fetch_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Fetch revenue and impression data for the given date range.
        
        Args:
            start_date: Start date for data fetch
            end_date: End date for data fetch
            
        Returns:
            Dictionary containing revenue and impressions data
        """
        # Format dates as YYYY-MM-DD
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        # Request async report
        report_url = self._request_report(start_str, end_str)
        
        # Poll for CSV data
        csv_content = self._poll_report_url(report_url)
        
        # Parse CSV
        report_data = self._parse_csv_response(csv_content)
        
        # Process and aggregate data
        platform_data = self._process_report_data(report_data)
        
        # Calculate totals
        total_revenue = 0.0
        total_impressions = 0
        total_clicks = 0
        
        for platform in ['android', 'ios']:
            total_revenue += platform_data[platform]['revenue']
            total_impressions += platform_data[platform]['impressions']
            total_clicks += platform_data[platform]['clicks']
        
        # Calculate overall eCPM
        total_ecpm = 0.0
        if total_impressions > 0:
            total_ecpm = (total_revenue / total_impressions) * 1000
        
        return {
            'revenue': total_revenue,
            'impressions': total_impressions,
            'ecpm': total_ecpm,
            'clicks': total_clicks,
            'network': self.get_network_name(),
            'date_range': {'start': start_str, 'end': end_str},
            'platform_data': platform_data,
        }
    
    def get_network_name(self) -> str:
        """Return the name of the network."""
        return "DT Exchange"
    
    def debug_auth(self) -> Dict[str, Any]:
        """
        Debug method to test authentication.
        
        Returns:
            Dictionary with auth status and token info
        """
        try:
            token = self._get_access_token()
            return {
                'success': True,
                'token_preview': f"{token[:20]}...{token[-10:]}" if len(token) > 30 else token,
                'expires_at': self._token_expires_at,
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }
    
    def debug_csv_content(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Debug method to fetch and display raw CSV content.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            Dictionary with CSV content and parsed rows
        """
        try:
            report_url = self._request_report(start_date, end_date)
            csv_content = self._poll_report_url(report_url)
            rows = self._parse_csv_response(csv_content)
            
            return {
                'success': True,
                'csv_preview': csv_content[:2000] if csv_content else "(empty)",
                'row_count': len(rows),
                'columns': list(rows[0].keys()) if rows else [],
                'sample_rows': rows[:5] if rows else [],
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }

    def debug_report_request(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Debug method to test report request.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            Dictionary with report URL or error
        """
        try:
            report_url = self._request_report(start_date, end_date)
            return {
                'success': True,
                'report_url': report_url,
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }
