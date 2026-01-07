"""
Pangle Reporting API v2 data fetcher implementation.
Uses Pangle Reporting API for fetching monetization data.
API Docs: https://www.pangleglobal.com/integration/reporting-api-v2
"""
import hashlib
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from .base_fetcher import NetworkDataFetcher


class PangleFetcher(NetworkDataFetcher):
    """Fetcher for Pangle monetization data using Reporting API v2."""
    
    # Pangle API endpoints
    BASE_URL = "https://open-api.pangleglobal.com"
    REPORT_ENDPOINT = "/union_pangle/open/api/rt/income"
    
    # API version and sign type (required by Pangle)
    API_VERSION = "2.0"
    SIGN_TYPE = "MD5"
    
    # Ad slot type mapping - Pangle numeric ad_slot_type to our standard categories
    AD_TYPE_MAP = {
        1: 'banner',       # In-feed ad
        2: 'banner',       # Banner (Horizontal)
        3: 'interstitial', # Splash ad
        4: 'interstitial', # Interstitial ad
        5: 'rewarded',     # Rewarded Video Ads
        6: 'interstitial', # Full Page Video Ads
        7: 'banner',       # Draw in-feed ad
        8: 'interstitial', # In-Stream Ads
        9: 'interstitial', # New interstitial ad
    }
    
    # Platform mapping
    PLATFORM_MAP = {
        'android': 'android',
        'ios': 'ios',
        'Android': 'android',
        'iOS': 'ios',
    }
    
    # Rate limit: 5 QPS (queries per second)
    RATE_LIMIT_DELAY = 0.2  # 200ms delay between requests
    
    def __init__(
        self,
        user_id: str,
        role_id: str,
        secure_key: str,
        time_zone: int = 0,
        currency: str = "usd",
        package_names: Optional[str] = None,
    ):
        """
        Initialize Pangle fetcher.
        
        Args:
            user_id: Pangle account ID
            role_id: Role ID (found near security key in dashboard)
            secure_key: Security Key from Pangle platform → SDK Integration → Data API
            time_zone: Timezone offset (0 for UTC, 8 for UTC+8). Default: 0 (UTC)
            currency: Currency for revenue ("usd" or "cny"). Default: "usd"
            package_names: Optional comma-separated package names to filter (e.g., "com.example.app,1234567890")
        """
        self.user_id = str(user_id)
        self.role_id = str(role_id)
        self.secure_key = secure_key
        self.time_zone = time_zone
        self.currency = currency.lower()
        self.package_names = [p.strip() for p in package_names.split(',') if p.strip()] if package_names else []
    
    def _generate_sign(self, params: Dict[str, Any]) -> str:
        """
        Generate MD5 signature for Pangle API.
        
        Pangle authentication requires:
        1. Sort all request parameters alphabetically
        2. Concatenate as k1=v1&k2=v2...
        3. Append secure_key
        4. Generate MD5 hash
        
        Args:
            params: Request parameters (without 'sign')
            
        Returns:
            MD5 signature string
        """
        # Sort parameters alphabetically by key
        sorted_params = sorted(params.items(), key=lambda x: x[0])
        
        # Build parameter string
        param_str = '&'.join([f"{k}={v}" for k, v in sorted_params])
        
        # Append secure key and generate MD5 hash
        sign_str = param_str + self.secure_key
        return hashlib.md5(sign_str.encode()).hexdigest()
    
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
    
    def _calculate_ecpm(self, revenue: float, impressions: int) -> float:
        """Calculate eCPM from revenue and impressions."""
        if impressions > 0:
            return (revenue / impressions) * 1000
        return 0.0
    
    def _fetch_single_day(self, date: datetime) -> List[Dict[str, Any]]:
        """
        Fetch data for a single day.
        
        Pangle API only supports single-day queries via the 'date' parameter.
        
        Args:
            date: Date to fetch data for
            
        Returns:
            List of data records for the day
        """
        date_str = date.strftime('%Y-%m-%d')
        
        # Build request parameters
        params = {
            'user_id': self.user_id,
            'role_id': self.role_id,
            'date': date_str,
            'version': self.API_VERSION,
            'sign_type': self.SIGN_TYPE,
            'time_zone': str(self.time_zone),
            'currency': self.currency,
        }
        
        # Generate signature
        params['sign'] = self._generate_sign(params)
        
        url = f"{self.BASE_URL}{self.REPORT_ENDPOINT}"
        
        response = requests.get(
            url,
            params=params,
            timeout=60
        )
        
        # Handle response
        if response.status_code != 200:
            error_msg = f"Pangle API HTTP error: {response.status_code}"
            try:
                error_msg += f" - {response.text[:500]}"
            except:
                pass
            raise Exception(error_msg)
        
        try:
            data = response.json()
        except Exception as e:
            raise Exception(f"Failed to parse Pangle response: {e}")
        
        # Check response code
        code = str(data.get('Code', ''))
        message = data.get('Message', '')
        
        if code == '101':
            raise Exception(
                "Pangle signature verification failed. "
                "Please check your user_id, role_id, and secure_key in config.yaml"
            )
        elif code == '102':
            raise Exception(
                "Pangle invalid user_id. "
                "Please check your user_id in config.yaml"
            )
        elif code == '103':
            raise Exception(f"Pangle invalid date format: {date_str}")
        elif code == '106':
            raise Exception(
                "Pangle QPS limit exceeded (5 queries/second). "
                "Please wait and retry."
            )
        elif code == '114':
            raise Exception(f"Pangle invalid parameter: {message}")
        elif code == '133':
            raise Exception(f"Pangle invalid region: {message}")
        elif code == 'PD0004':
            # Success but no data
            return []
        elif code != '100':
            raise Exception(f"Pangle API error: Code={code}, Message={message}")
        
        # Extract data - response format: {"Code": "100", "Data": {"2021-01-12": [...]}}
        response_data = data.get('Data', {})
        
        # Data is nested under date string key
        records = []
        for date_key, day_records in response_data.items():
            if isinstance(day_records, list):
                records.extend(day_records)
        
        return records
    
    def fetch_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Fetch Pangle monetization data for the specified date range.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            Dictionary containing revenue, impressions, and platform breakdown
        """
        # Initialize result structure
        result = {
            'revenue': 0.0,
            'impressions': 0,
            'ecpm': 0.0,
            'network': self.get_network_name(),
            'date_range': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            },
            'platform_data': {
                'android': self._create_empty_platform_data(),
                'ios': self._create_empty_platform_data(),
            }
        }
        
        # Iterate through each day in the range
        current_date = start_date
        while current_date <= end_date:
            # Fetch data for the current day
            records = self._fetch_single_day(current_date)
            
            # Process records
            for record in records:
                if not isinstance(record, dict):
                    continue
                
                # Filter by package_names if configured
                if self.package_names:
                    record_package = record.get('package_name', '')
                    if record_package not in self.package_names:
                        continue
                
                # Extract metrics
                revenue = float(record.get('revenue', 0) or 0)
                impressions = int(record.get('show', 0) or 0)
                clicks = int(record.get('click', 0) or 0)
                requests = int(record.get('request', 0) or 0)
                fills = int(record.get('return', 0) or 0)
                
                # Determine platform
                os_raw = record.get('os', '').lower()
                platform = self.PLATFORM_MAP.get(os_raw, os_raw)
                if platform not in ['android', 'ios']:
                    # Skip unknown platforms or aggregate to a default
                    continue
                
                # Determine ad type
                ad_slot_type = record.get('ad_slot_type')
                try:
                    ad_slot_type = int(ad_slot_type)
                except (TypeError, ValueError):
                    ad_slot_type = None
                
                ad_type = self.AD_TYPE_MAP.get(ad_slot_type, None)
                
                # Update totals
                result['revenue'] += revenue
                result['impressions'] += impressions
                
                # Update platform data
                platform_data = result['platform_data'][platform]
                platform_data['revenue'] += revenue
                platform_data['impressions'] += impressions
                platform_data['clicks'] += clicks
                platform_data['requests'] += requests
                platform_data['fills'] += fills
                
                # Update ad type data if valid
                if ad_type and ad_type in platform_data['ad_data']:
                    ad_data = platform_data['ad_data'][ad_type]
                    ad_data['revenue'] += revenue
                    ad_data['impressions'] += impressions
                    ad_data['clicks'] += clicks
                    ad_data['requests'] += requests
                    ad_data['fills'] += fills
            
            # Rate limit delay (5 QPS limit)
            time.sleep(self.RATE_LIMIT_DELAY)
            
            # Move to next day
            current_date += timedelta(days=1)
        
        # Calculate eCPMs
        result['ecpm'] = self._calculate_ecpm(result['revenue'], result['impressions'])
        
        for platform in ['android', 'ios']:
            platform_data = result['platform_data'][platform]
            platform_data['ecpm'] = self._calculate_ecpm(
                platform_data['revenue'],
                platform_data['impressions']
            )
            
            for ad_type in ['banner', 'interstitial', 'rewarded']:
                ad_data = platform_data['ad_data'][ad_type]
                ad_data['ecpm'] = self._calculate_ecpm(
                    ad_data['revenue'],
                    ad_data['impressions']
                )
        
        return result
    
    def get_network_name(self) -> str:
        """Return the network name."""
        return "Pangle Bidding"
