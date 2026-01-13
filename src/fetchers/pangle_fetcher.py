"""
Pangle Reporting API v2 data fetcher implementation.
Async version using aiohttp with retry support.
API Docs: https://www.pangleglobal.com/integration/reporting-api-v2
"""
import hashlib
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from .base_fetcher import NetworkDataFetcher, FetchResult
from ..enums import Platform, AdType, NetworkName


logger = logging.getLogger(__name__)


class PangleFetcher(NetworkDataFetcher):
    """Fetcher for Pangle monetization data using Reporting API v2."""
    
    # Pangle API endpoints
    BASE_URL = "https://open-api.pangleglobal.com"
    REPORT_ENDPOINT = "/union_pangle/open/api/rt/income"
    
    # API version and sign type (required by Pangle)
    API_VERSION = "2.0"
    SIGN_TYPE = "MD5"
    
    # Ad slot type mapping - Pangle numeric ad_slot_type to AdType enum
    AD_TYPE_MAP = {
        1: AdType.BANNER,       # In-feed ad
        2: AdType.BANNER,       # Banner (Horizontal)
        3: AdType.INTERSTITIAL, # Splash ad
        4: AdType.INTERSTITIAL, # Interstitial ad
        5: AdType.REWARDED,     # Rewarded Video Ads
        6: AdType.INTERSTITIAL, # Full Page Video Ads
        7: AdType.BANNER,       # Draw in-feed ad
        8: AdType.INTERSTITIAL, # In-Stream Ads
        9: AdType.INTERSTITIAL, # New interstitial ad
    }
    
    # Platform mapping
    PLATFORM_MAP = {
        'android': Platform.ANDROID,
        'ios': Platform.IOS,
        'Android': Platform.ANDROID,
        'iOS': Platform.IOS,
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
            package_names: Optional comma-separated package names to filter
        """
        super().__init__()
        self.user_id = str(user_id)
        self.role_id = str(role_id)
        self.secure_key = secure_key
        self.time_zone = time_zone
        self.currency = currency.lower()
        self.package_names = [p.strip() for p in package_names.split(',') if p.strip()] if package_names else []
    
    def _generate_sign(self, params: Dict[str, Any]) -> str:
        """
        Generate MD5 signature for Pangle API.
        
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
    
    async def _fetch_single_day(self, date: datetime) -> List[Dict[str, Any]]:
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
        
        try:
            data = await self._get_json(url, params=params)
        except Exception as e:
            raise Exception(f"Pangle API error: {str(e)}")
        
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
    
    async def fetch_data(self, start_date: datetime, end_date: datetime) -> FetchResult:
        """
        Fetch Pangle monetization data for the specified date range.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            FetchResult containing revenue and impressions data
        """
        # Initialize data structures using base class helpers
        ad_data = self._init_ad_data()
        platform_data = self._init_platform_data()
        
        # Daily breakdown data: {date_str: {platform: {ad_type: {revenue, impressions}}}}
        daily_data = {}
        
        total_revenue = 0.0
        total_impressions = 0
        
        # Iterate through each day in the range
        current_date = start_date
        while current_date <= end_date:
            # Get date key for daily breakdown
            date_key = current_date.strftime('%Y-%m-%d')
            
            # Fetch data for the current day
            records = await self._fetch_single_day(current_date)
            
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
                
                # Determine platform
                os_raw = record.get('os', '').lower()
                platform = self._normalize_platform(os_raw)
                
                # Determine ad type
                ad_slot_type = record.get('ad_slot_type')
                try:
                    ad_slot_type = int(ad_slot_type)
                except (TypeError, ValueError):
                    ad_slot_type = None
                
                ad_type = self.AD_TYPE_MAP.get(ad_slot_type, AdType.INTERSTITIAL)
                
                # Accumulate totals
                total_revenue += revenue
                total_impressions += impressions
                
                # Use base class helper to accumulate metrics
                self._accumulate_metrics(
                    platform_data, ad_data,
                    platform, ad_type,
                    revenue, impressions
                )
                
                # Accumulate daily breakdown
                if date_key not in daily_data:
                    daily_data[date_key] = {}
                if platform.value not in daily_data[date_key]:
                    daily_data[date_key][platform.value] = {}
                if ad_type.value not in daily_data[date_key][platform.value]:
                    daily_data[date_key][platform.value][ad_type.value] = {'revenue': 0.0, 'impressions': 0}
                
                daily_data[date_key][platform.value][ad_type.value]['revenue'] += revenue
                daily_data[date_key][platform.value][ad_type.value]['impressions'] += impressions
            
            # Rate limit delay (5 QPS limit)
            await asyncio.sleep(self.RATE_LIMIT_DELAY)
            
            # Move to next day
            current_date += timedelta(days=1)
        
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
        """Return the network name."""
        return NetworkName.PANGLE.display_name
    
    def get_network_enum(self) -> NetworkName:
        """Return the NetworkName enum."""
        return NetworkName.PANGLE
