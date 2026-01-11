"""
Moloco Publisher Summary API data fetcher implementation.
Uses Moloco Publisher Summary API for fetching monetization data.
API Docs: https://help.publisher.moloco.com/hc/en-us/articles/26777697929111-Get-performance-data-using-the-Publisher-Summary-API
"""
import requests
from datetime import datetime
from typing import Dict, Any, Optional
from .base_fetcher import NetworkDataFetcher


class MolocoFetcher(NetworkDataFetcher):
    """Fetcher for Moloco Publisher monetization data using Publisher Summary API."""
    
    # Moloco Publisher API endpoints
    AUTH_URL = "https://sdkpubapi.moloco.com/api/adcloud/publisher/v1/auth/tokens"
    SUMMARY_URL = "https://sdkpubapi.moloco.com/api/adcloud/publisher/v1/sdk/summary"
    
    # Ad type mapping - Moloco inventory_type to our standard categories
    AD_TYPE_MAP = {
        'BANNER': 'banner',
        'INTERSTITIAL': 'interstitial',
        'REWARDED': 'rewarded',
        'REWARDED_VIDEO': 'rewarded',
        'REWARD_VIDEO': 'rewarded',
        'REWARDED_INTERSTITIAL': 'rewarded',
        'NATIVE': 'banner',
        'MREC': 'banner',
        'APP_OPEN': 'interstitial',
        'APPOPEN': 'interstitial',
    }
    
    # Platform mapping
    PLATFORM_MAP = {
        'ANDROID': 'android',
        'IOS': 'ios',
        'android': 'android',
        'ios': 'ios',
        'PLATFORM_TYPE_ANDROID': 'android',
        'PLATFORM_TYPE_IOS': 'ios',
    }
    
    def __init__(
        self,
        email: str,
        password: str,
        platform_id: str,
        publisher_id: str,
        app_bundle_ids: Optional[str] = None,
        time_zone: str = "UTC",
        ad_unit_mapping: Optional[Dict[str, str]] = None
    ):
        """
        Initialize Moloco Publisher fetcher.
        
        Args:
            email: Moloco Publisher login email
            password: Moloco Publisher password
            platform_id: Moloco Platform ID (used as workplace_id for auth token)
            publisher_id: Moloco Publisher ID (used for API metric requests)
            app_bundle_ids: Optional comma-separated app bundle IDs to filter
            time_zone: Timezone for data aggregation (default: UTC)
            ad_unit_mapping: Optional dict mapping ad_unit_id to ad_type (banner/interstitial/rewarded)
        """
        self.email = email
        self.password = password
        self.platform_id = platform_id
        self.publisher_id = publisher_id
        self.app_bundle_ids = [a.strip() for a in app_bundle_ids.split(',') if a.strip()] if app_bundle_ids else []
        self.time_zone = time_zone
        self.ad_unit_mapping = ad_unit_mapping or {}
        self._access_token = None
        
    def _get_access_token(self) -> str:
        """
        Get access token from Moloco auth endpoint.
        Token is valid for 60 minutes.
        
        Returns:
            Access token string
        """
        if self._access_token:
            # Try to refresh existing token
            try:
                return self._refresh_token()
            except Exception:
                self._access_token = None
        
        # Get new token
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        
        payload = {
            'email': self.email,
            'password': self.password,
            'workplace_id': self.platform_id,
        }
        
        response = requests.post(
            self.AUTH_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            error_msg = f"Moloco auth error: {response.status_code}"
            try:
                error_data = response.json()
                error_msg += f" - {error_data.get('message', error_data.get('error', response.text))}"
            except:
                error_msg += f" - {response.text[:500]}"
            raise Exception(error_msg)
        
        data = response.json()
        
        # Check if password update is required
        token_type = data.get('token_type', '')
        if token_type == 'UPDATE_PASSWORD':
            raise Exception(
                "Moloco requires password update. "
                "Please log in to the Moloco Publisher Portal to update your password."
            )
        
        self._access_token = data.get('token')
        if not self._access_token:
            raise Exception(f"No token in response: {data}")
        
        return self._access_token
    
    def _refresh_token(self) -> str:
        """
        Refresh existing access token before it expires.
        
        Returns:
            New access token string
        """
        headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {self._access_token}',
        }
        
        response = requests.put(
            self.AUTH_URL,
            headers=headers,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"Token refresh failed: {response.status_code}")
        
        data = response.json()
        self._access_token = data.get('token')
        
        if not self._access_token:
            raise Exception(f"No token in refresh response: {data}")
        
        return self._access_token
        
    def _create_empty_platform_data(self) -> Dict[str, Any]:
        """Create empty platform data structure."""
        return {
            'revenue': 0.0,
            'impressions': 0,
            'ecpm': 0.0,
            'requests': 0,
            'fills': 0,
            'clicks': 0,
            'ad_data': {
                'banner': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0, 'requests': 0, 'fills': 0, 'clicks': 0},
                'interstitial': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0, 'requests': 0, 'fills': 0, 'clicks': 0},
                'rewarded': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0, 'requests': 0, 'fills': 0, 'clicks': 0},
            }
        }
    
    def _make_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make POST request to Moloco Publisher Summary API.
        
        Args:
            payload: Request body (JSON payload)
            
        Returns:
            API response as dictionary
        """
        # Get access token (will refresh if needed)
        token = self._get_access_token()
        
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}',
        }
        
        response = requests.post(
            self.SUMMARY_URL,
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 401:
            # Token expired, get new one and retry
            self._access_token = None
            token = self._get_access_token()
            headers['Authorization'] = f'Bearer {token}'
            
            response = requests.post(
                self.SUMMARY_URL,
                headers=headers,
                json=payload,
                timeout=60
            )
        
        if response.status_code != 200:
            error_msg = f"Moloco API error: {response.status_code}"
            try:
                error_data = response.json()
                error_msg += f" - {error_data.get('message', error_data.get('error', response.text))}"
            except:
                error_msg += f" - {response.text[:500]}"
            raise Exception(error_msg)
        
        return response.json()
    
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
        
        # Build POST request body for Publisher Summary API
        # API Docs: https://help.publisher.moloco.com/hc/en-us/articles/26777697929111
        payload = {
            'publisher_id': self.publisher_id,
            'date_range': {
                'start': start_str,
                'end': end_str
            },
            'dimensions': ['UTC_DATE', 'DEVICE_OS', 'AD_UNIT_ID'],
            'metrics': ['REVENUE', 'IMPRESSIONS', 'REQUESTS', 'FILLS', 'CLICKS'],
        }
        
        # Add app filter if specified (using app store IDs like bundle ID or iTunes ID)
        if self.app_bundle_ids:
            payload['dimension_filters'] = [
                {
                    'dimension': 'PUBLISHER_APP_STORE_ID',
                    'values': self.app_bundle_ids
                }
            ]
        
        # Make API request
        response_data = self._make_request(payload)
        
        # Parse response
        return self._parse_response(response_data, start_str, end_str)
    
    def _parse_response(
        self, 
        response_data: Dict[str, Any], 
        start_str: str, 
        end_str: str
    ) -> Dict[str, Any]:
        """
        Parse Moloco API response into standardized format.
        
        Response format:
        {
          "rows": [
            {
              "device": { "os": "IOS" | "ANDROID" },
              "ad_unit": { "inventory_type": "BANNER" | "INTERSTITIAL" | "REWARD_VIDEO" },
              "metric": { "revenue": float, "impressions": int, "requests": int, "clicks": int, "ecpm": float }
            }
          ]
        }
        
        Args:
            response_data: Raw API response
            start_str: Start date string
            end_str: End date string
            
        Returns:
            Standardized data dictionary
        """
        # Initialize result structure
        result = {
            'revenue': 0.0,
            'impressions': 0,
            'ecpm': 0.0,
            'requests': 0,
            'fills': 0,
            'clicks': 0,
            'network': self.get_network_name(),
            'date_range': {'start': start_str, 'end': end_str},
            'platform_data': {
                'android': self._create_empty_platform_data(),
                'ios': self._create_empty_platform_data(),
            }
        }
        
        # Parse rows from response
        rows = response_data.get('rows', [])
        
        if not rows:
            return result
        
        for row in rows:
            if not isinstance(row, dict):
                continue
            
            # Extract metrics from row.metric object
            metric = row.get('metric', {})
            revenue = float(metric.get('revenue', 0) or 0)
            # impressions comes as string from API
            impressions_raw = metric.get('impressions', 0) or 0
            impressions = int(impressions_raw) if impressions_raw else 0
            requests_raw = metric.get('requests', 0) or 0
            requests = int(requests_raw) if requests_raw else 0
            clicks_raw = metric.get('clicks', 0) or 0
            clicks = int(clicks_raw) if clicks_raw else 0
            # fills can be calculated from fill_rate * requests or use impressions as approximation
            fill_rate = float(metric.get('fill_rate', 0) or 0)
            fills = int(requests * fill_rate) if requests > 0 else impressions
            
            # Extract platform from device.os
            device = row.get('device', {})
            platform_raw = device.get('os', 'ANDROID')
            platform = self.PLATFORM_MAP.get(str(platform_raw).upper(), 'android')
            
            # Ensure platform is valid
            if platform not in ['android', 'ios']:
                platform = 'android'
            
            # Extract ad type - first try ad_unit_mapping, then inventory_type, then default
            ad_unit = row.get('ad_unit', {})
            ad_unit_id = ad_unit.get('ad_unit_id', '')
            
            # Priority: 1) ad_unit_mapping from config, 2) inventory_type from API, 3) default 'banner'
            if ad_unit_id and ad_unit_id in self.ad_unit_mapping:
                ad_type = self.ad_unit_mapping[ad_unit_id]
            else:
                inventory_type = ad_unit.get('inventory_type', '')
                if inventory_type:
                    ad_type = self.AD_TYPE_MAP.get(str(inventory_type).upper(), 'banner')
                else:
                    ad_type = 'banner'
            
            # Aggregate totals
            result['revenue'] += revenue
            result['impressions'] += impressions
            result['requests'] += requests
            result['fills'] += fills
            result['clicks'] += clicks
            
            # Aggregate by platform
            result['platform_data'][platform]['revenue'] += revenue
            result['platform_data'][platform]['impressions'] += impressions
            result['platform_data'][platform]['requests'] += requests
            result['platform_data'][platform]['fills'] += fills
            result['platform_data'][platform]['clicks'] += clicks
            
            # Aggregate by ad type within platform
            result['platform_data'][platform]['ad_data'][ad_type]['revenue'] += revenue
            result['platform_data'][platform]['ad_data'][ad_type]['impressions'] += impressions
            result['platform_data'][platform]['ad_data'][ad_type]['requests'] += requests
            result['platform_data'][platform]['ad_data'][ad_type]['fills'] += fills
            result['platform_data'][platform]['ad_data'][ad_type]['clicks'] += clicks
        
        # Calculate eCPMs
        if result['impressions'] > 0:
            result['ecpm'] = (result['revenue'] / result['impressions']) * 1000
        
        for platform in ['android', 'ios']:
            p_data = result['platform_data'][platform]
            if p_data['impressions'] > 0:
                p_data['ecpm'] = (p_data['revenue'] / p_data['impressions']) * 1000
            
            for ad_type in ['banner', 'interstitial', 'rewarded']:
                ad_data = p_data['ad_data'][ad_type]
                if ad_data['impressions'] > 0:
                    ad_data['ecpm'] = (ad_data['revenue'] / ad_data['impressions']) * 1000
        
        return result
    
    def get_network_name(self) -> str:
        """Return the name of the network."""
        return "Moloco Bidding"

