"""
Chartboost Mediation Reporting API data fetcher implementation.
API Docs: https://docs.chartboost.com/en/mediation/reference/mediation-reporting-api/
"""
import os
import json
import requests
from datetime import datetime
from typing import Dict, Any, Optional, List
from .base_fetcher import NetworkDataFetcher


class ChartboostFetcher(NetworkDataFetcher):
    """Fetcher for Chartboost Mediation publisher data using Reporting API."""
    
    # Chartboost API endpoints
    AUTH_URL = "https://api.chartboost.com/v5/oauth/token"
    REPORT_URL = "https://helium-api.chartboost.com/v2/publisher/metrics"
    
    # Token cache file path
    TOKEN_CACHE_FILE = "credentials/chartboost_token.json"
    
    # Ad type mapping - map Chartboost placement types to standard types
    AD_TYPE_MAP = {
        'interstitial': 'interstitial',
        'rewarded': 'rewarded',
        'banner': 'banner',
        'rewarded_interstitial': 'rewarded',
        'adaptive_banner': 'banner',
    }
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        app_ids: Optional[str] = None,
        time_zone: str = "UTC",
        app_platform_map: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize Chartboost fetcher.
        
        Args:
            client_id: Chartboost OAuth Client ID
            client_secret: Chartboost OAuth Client Secret
            app_ids: Optional comma-separated app IDs to filter
            time_zone: Timezone for data (UTC or America/Los_Angeles)
            app_platform_map: Optional dict mapping app_id to platform (android/ios)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.app_ids = [aid.strip() for aid in app_ids.split(',') if aid.strip()] if app_ids else []
        self.time_zone = time_zone
        self.app_platform_map = app_platform_map or {}
        
        # Token cache
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
    
    def _load_cached_token(self) -> bool:
        """
        Load cached token from file if valid.
        
        Returns:
            True if valid token loaded, False otherwise
        """
        if not os.path.exists(self.TOKEN_CACHE_FILE):
            return False
        
        try:
            with open(self.TOKEN_CACHE_FILE, 'r') as f:
                cache = json.load(f)
            
            expires_at_str = cache.get('expires_at')
            access_token = cache.get('access_token')
            
            if not expires_at_str or not access_token:
                return False
            
            expires_at = datetime.fromisoformat(expires_at_str)
            
            # Check if token is still valid (with 5 min buffer)
            if datetime.now() < expires_at:
                self._access_token = access_token
                self._token_expires_at = expires_at
                return True
            
            return False
        except Exception:
            return False
    
    def _save_token_cache(self, access_token: str, expires_in: int) -> None:
        """
        Save token to cache file.
        
        Args:
            access_token: OAuth access token
            expires_in: Token validity in seconds
        """
        try:
            # Calculate expiry time with 5 min buffer
            from datetime import timedelta
            expires_at = datetime.now() + timedelta(seconds=expires_in - 300)
            
            cache = {
                'access_token': access_token,
                'expires_at': expires_at.isoformat(),
            }
            
            # Ensure credentials directory exists
            os.makedirs(os.path.dirname(self.TOKEN_CACHE_FILE), exist_ok=True)
            
            with open(self.TOKEN_CACHE_FILE, 'w') as f:
                json.dump(cache, f, indent=2)
        except Exception:
            pass  # Token caching is optional
    
    def _get_access_token(self) -> str:
        """
        Get OAuth 2.0 access token from Chartboost.
        Uses cached token if still valid.
        
        Returns:
            Access token string
            
        Raises:
            Exception: If authentication fails
        """
        # Check cached token
        if self._access_token and self._token_expires_at:
            if datetime.now() < self._token_expires_at:
                return self._access_token
        
        # Try loading from file cache
        if self._load_cached_token():
            return self._access_token
        
        # Request new token
        payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'audience': 'https://public.api.gateway.chartboost.com',
            'grant_type': 'client_credentials',
        }
        
        headers = {
            'Content-Type': 'application/json',
        }
        
        response = requests.post(
            self.AUTH_URL,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        if response.status_code != 200:
            error_msg = f"Chartboost authentication failed ({response.status_code})"
            try:
                error_data = response.json()
                if 'error_description' in error_data:
                    error_msg += f": {error_data['error_description']}"
                elif 'error' in error_data:
                    error_msg += f": {error_data['error']}"
            except:
                error_msg += f": {response.text[:200]}"
            raise Exception(error_msg)
        
        data = response.json()
        access_token = data.get('access_token')
        expires_in = data.get('expires_in', 86400)
        
        if not access_token:
            raise Exception("Chartboost authentication failed: No access_token in response")
        
        # Cache token
        from datetime import timedelta
        self._access_token = access_token
        self._token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)
        
        # Save to file cache
        self._save_token_cache(access_token, expires_in)
        
        return access_token
    
    def _create_empty_platform_data(self) -> Dict[str, Any]:
        """Create empty platform data structure."""
        return {
            'revenue': 0.0,
            'impressions': 0,
            'ecpm': 0.0,
            'requests': 0,
            'ad_data': {
                'banner': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0, 'requests': 0},
                'interstitial': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0, 'requests': 0},
                'rewarded': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0, 'requests': 0},
            }
        }
    
    def _fetch_report_data(
        self,
        start_date: str,
        end_date: str,
    ) -> List[Dict[str, Any]]:
        """
        Fetch report data from Chartboost API.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            List of report data rows
        """
        access_token = self._get_access_token()
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }
        
        # Build request payload
        # Using 'app' dimension to potentially map to platforms later
        payload = {
            'date_min': start_date,
            'date_max': end_date,
            'timezone': self.time_zone,
            'dimensions': ['date', 'app', 'placement_type'],
            'metrics': ['requests', 'impressions', 'estimated_earnings', 'ecpm', 'fill_rate'],
        }
        
        # Add app filter if specified
        if self.app_ids:
            payload['filters'] = {'apps': self.app_ids}
        
        response = requests.post(
            self.REPORT_URL,
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 401:
            # Token might be invalid, clear cache and retry once
            self._access_token = None
            self._token_expires_at = None
            if os.path.exists(self.TOKEN_CACHE_FILE):
                os.remove(self.TOKEN_CACHE_FILE)
            
            access_token = self._get_access_token()
            headers['Authorization'] = f'Bearer {access_token}'
            
            response = requests.post(
                self.REPORT_URL,
                headers=headers,
                json=payload,
                timeout=60
            )
        
        if response.status_code != 200:
            error_msg = f"Chartboost API error: {response.status_code}"
            try:
                error_data = response.json()
                error_msg += f" - {error_data}"
            except:
                error_msg += f" - {response.text[:500]}"
            raise Exception(error_msg)
        
        # Parse response
        try:
            data = response.json()
            return data.get('data', [])
        except Exception as e:
            raise Exception(f"Failed to parse Chartboost response: {e}")
    
    def _process_report_data(self, report_data: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Process report data and aggregate by platform.
        
        Args:
            report_data: List of report rows from API
            
        Returns:
            Dictionary with platform_data structure
        """
        platform_data = {
            'android': self._create_empty_platform_data(),
            'ios': self._create_empty_platform_data(),
        }
        
        # Track data that couldn't be mapped to a platform
        unmapped_data = self._create_empty_platform_data()
        
        for row in report_data:
            if not isinstance(row, dict):
                continue
            
            # Get app ID and map to platform
            app_id = row.get('app', '')
            platform = self.app_platform_map.get(app_id)
            
            # Determine ad type from placement_type
            placement_type = row.get('placement_type', '').lower()
            ad_type = self.AD_TYPE_MAP.get(placement_type, 'interstitial')
            
            # Extract metrics
            rev = float(row.get('estimated_earnings', 0) or 0)
            imps = int(row.get('impressions', 0) or 0)
            reqs = int(row.get('requests', 0) or 0)
            
            if platform:
                # Aggregate platform totals
                platform_data[platform]['revenue'] += rev
                platform_data[platform]['impressions'] += imps
                platform_data[platform]['requests'] += reqs
                
                # Aggregate by ad type
                platform_data[platform]['ad_data'][ad_type]['revenue'] += rev
                platform_data[platform]['ad_data'][ad_type]['impressions'] += imps
                platform_data[platform]['ad_data'][ad_type]['requests'] += reqs
            else:
                # Track unmapped data
                unmapped_data['revenue'] += rev
                unmapped_data['impressions'] += imps
                unmapped_data['requests'] += reqs
                unmapped_data['ad_data'][ad_type]['revenue'] += rev
                unmapped_data['ad_data'][ad_type]['impressions'] += imps
                unmapped_data['ad_data'][ad_type]['requests'] += reqs
        
        # If no platform mapping provided, distribute unmapped data as "unknown"
        if unmapped_data['impressions'] > 0 or unmapped_data['revenue'] > 0:
            platform_data['unknown'] = unmapped_data
        
        # Calculate eCPMs
        for platform in platform_data.keys():
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
        
        # Fetch report data
        report_data = self._fetch_report_data(start_str, end_str)
        
        # Process and aggregate data
        platform_data = self._process_report_data(report_data)
        
        # Calculate totals
        total_revenue = 0.0
        total_impressions = 0
        total_requests = 0
        
        for platform in platform_data.keys():
            total_revenue += platform_data[platform]['revenue']
            total_impressions += platform_data[platform]['impressions']
            total_requests += platform_data[platform]['requests']
        
        # Calculate overall eCPM
        total_ecpm = 0.0
        if total_impressions > 0:
            total_ecpm = (total_revenue / total_impressions) * 1000
        
        return {
            'revenue': total_revenue,
            'impressions': total_impressions,
            'ecpm': total_ecpm,
            'requests': total_requests,
            'network': self.get_network_name(),
            'date_range': {'start': start_str, 'end': end_str},
            'platform_data': platform_data,
        }
    
    def get_network_name(self) -> str:
        """Return the name of the network."""
        return "Chartboost"
    
    # ==================== DEBUG METHODS ====================
    
    def _test_auth(self) -> bool:
        """
        Test OAuth authentication to Chartboost API.
        
        Returns:
            True if authentication successful, False otherwise
        """
        print("\n🔐 Testing Chartboost OAuth authentication...")
        print(f"   Auth URL: {self.AUTH_URL}")
        print(f"   Client ID: {self.client_id[:8]}...{self.client_id[-4:]}")
        
        try:
            token = self._get_access_token()
            print(f"   ✅ Authentication successful!")
            print(f"   Token: {token[:20]}...{token[-10:]}")
            return True
        except Exception as e:
            print(f"   ❌ Authentication failed: {e}")
            return False
    
    def _test_report_request(self, start_date: datetime, end_date: datetime) -> None:
        """
        Test report request and print raw response for debugging.
        
        Args:
            start_date: Start date for report
            end_date: End date for report
        """
        print("\n📊 Testing Chartboost report request...")
        print(f"   Report URL: {self.REPORT_URL}")
        print(f"   Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"   Timezone: {self.time_zone}")
        
        if self.app_ids:
            print(f"   App filter: {self.app_ids}")
        
        try:
            report_data = self._fetch_report_data(
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )
            
            print(f"   ✅ Report request successful!")
            print(f"   Rows returned: {len(report_data)}")
            
            if report_data:
                print(f"\n   📄 Sample row:")
                sample = report_data[0]
                for key, value in sample.items():
                    print(f"      {key}: {value}")
                
                # Track unique values
                apps = set()
                placement_types = set()
                
                for row in report_data:
                    if row.get('app'):
                        apps.add(row.get('app'))
                    if row.get('placement_type'):
                        placement_types.add(row.get('placement_type'))
                
                print(f"\n   📋 Unique values:")
                print(f"      Apps: {apps}")
                print(f"      Placement types: {placement_types}")
            else:
                print(f"   ⚠️ No data returned for this date range")
                
        except Exception as e:
            print(f"   ❌ Report request failed: {e}")
