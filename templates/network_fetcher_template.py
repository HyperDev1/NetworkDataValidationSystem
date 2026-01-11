"""
[NetworkName] data fetcher implementation.
Async version using aiohttp with retry support.
API Docs: [API_DOCUMENTATION_URL]

PLACEHOLDER TEMPLATE - Replace all [PLACEHOLDERS] with actual values
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from .base_fetcher import NetworkDataFetcher, FetchResult
from ..enums import Platform, AdType, NetworkName

logger = logging.getLogger(__name__)


class NetworkNameFetcher(NetworkDataFetcher):
    """Async fetcher for [NetworkName] monetization data."""
    
    # ============================================================
    # API CONFIGURATION - Update based on API documentation
    # ============================================================
    BASE_URL = "https://api.networkname.com"
    AUTH_ENDPOINT = "/v1/auth/tokens"      # Login endpoint (if session-based)
    REPORT_ENDPOINT = "/v1/reports/summary"  # Report endpoint
    
    # ============================================================
    # ENUM-BASED MAPPING CONSTANTS - Update based on API response values
    # ============================================================
    
    # Platform mapping: API value → Platform enum
    PLATFORM_MAP = {
        'ANDROID': Platform.ANDROID,
        'IOS': Platform.IOS,
        'android': Platform.ANDROID,
        'ios': Platform.IOS,
        'PLATFORM_TYPE_ANDROID': Platform.ANDROID,
        'PLATFORM_TYPE_IOS': Platform.IOS,
        # Add more mappings based on API response
    }
    
    # Ad type mapping: API value → AdType enum
    AD_TYPE_MAP = {
        'BANNER': AdType.BANNER,
        'INTERSTITIAL': AdType.INTERSTITIAL,
        'REWARDED': AdType.REWARDED,
        'REWARDED_VIDEO': AdType.REWARDED,
        'REWARD_VIDEO': AdType.REWARDED,
        'NATIVE': AdType.BANNER,
        'MREC': AdType.BANNER,
        'APP_OPEN': AdType.INTERSTITIAL,
        # Add more mappings based on API response
    }
    
    # ============================================================
    # RESPONSE FIELD NAMES - Update based on API response
    # ============================================================
    RESPONSE_DATA_KEY = "data"        # Key containing data array (or None if root)
    PLATFORM_FIELD = "platform_type"  # Field name for platform
    AD_TYPE_FIELD = "inventory_type"  # Field name for ad type
    REVENUE_FIELD = "revenue"         # Field name for revenue
    IMPRESSIONS_FIELD = "impressions" # Field name for impressions
    
    # Revenue scaling (1 if USD, 1000000 if micros, 100 if cents)
    REVENUE_SCALE = 1
    
    def __init__(
        self,
        api_key: str,
        publisher_id: str,
        # Add more parameters as needed
        app_ids: Optional[str] = None,
    ):
        """
        Initialize [NetworkName] fetcher.
        
        Args:
            api_key: API key or access token
            publisher_id: Publisher/Account ID
            app_ids: Optional comma-separated app IDs to filter
        """
        super().__init__()  # ⚠️ Required - creates aiohttp session
        self.api_key = api_key
        self.publisher_id = publisher_id
        self.app_ids = [a.strip() for a in app_ids.split(',') if a.strip()] if app_ids else []
        self._access_token = None  # For session-based auth
    
    # ============================================================
    # DEBUG METHODS - Use these for testing
    # ============================================================
    
    async def _test_auth(self) -> bool:
        """
        Test authentication - DEBUG METHOD.
        Call this first to verify credentials work.
        """
        print("\n" + "="*60)
        print("🔐 AUTH TEST")
        print("="*60)
        
        headers = self._get_auth_headers()
        
        print(f"\n📤 REQUEST:")
        print(f"   URL: {self.BASE_URL}{self.AUTH_ENDPOINT}")
        
        try:
            # Use base class async method
            response = await self._get_json(
                f"{self.BASE_URL}{self.AUTH_ENDPOINT}",
                headers=headers
            )
            
            print(f"\n📥 RESPONSE:")
            import json
            print(f"   Body:\n{json.dumps(response, indent=2)[:1000]}")
            
            return True
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def _test_report_request(self, start_date: datetime, end_date: datetime) -> Dict:
        """
        Test report request - DEBUG METHOD.
        Call this after auth test passes.
        """
        print("\n" + "="*60)
        print("📊 REPORT REQUEST TEST")
        print("="*60)
        
        headers = self._get_auth_headers()
        payload = self._build_report_payload(start_date, end_date)
        
        print(f"\n📤 REQUEST:")
        print(f"   URL: {self.BASE_URL}{self.REPORT_ENDPOINT}")
        print(f"   Method: POST")
        import json
        print(f"   Payload:\n{json.dumps(payload, indent=2)}")
        
        try:
            response_json = await self._post_json(
                f"{self.BASE_URL}{self.REPORT_ENDPOINT}",
                headers=headers,
                json=payload
            )
            
            print(f"\n📥 RESPONSE:")
            response_str = json.dumps(response_json, indent=2)
            if len(response_str) > 3000:
                print(f"   Body (truncated):\n{response_str[:3000]}...")
            else:
                print(f"   Body:\n{response_str}")
            return response_json
                
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    # ============================================================
    # HELPER METHODS
    # ============================================================
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get headers with authentication."""
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
    
    def _build_report_payload(self, start_date: datetime, end_date: datetime) -> Dict:
        """Build report request payload."""
        # Adjust based on API documentation
        payload = {
            'publisher_id': self.publisher_id,
            'date_range': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            },
            'dimensions': ['platform', 'ad_type'],  # Adjust field names
            'metrics': ['revenue', 'impressions'],
            'timezone': 'UTC'
        }
        
        # Add app filter if specified
        if self.app_ids:
            payload['app_ids'] = self.app_ids
        
        return payload
    
    # ============================================================
    # MAIN METHODS
    # ============================================================
    
    async def fetch_data(self, start_date: datetime, end_date: datetime) -> FetchResult:
        """
        Fetch revenue and impression data for the given date range.
        
        Uses aiohttp for async HTTP requests with retry support.
        
        Args:
            start_date: Start date for data fetch
            end_date: End date for data fetch
            
        Returns:
            FetchResult containing revenue and impressions data
        """
        logger.debug(f"Fetching {self.get_network_name()} data for {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Initialize data structures using base class helpers
        ad_data = self._init_ad_data()
        platform_data = self._init_platform_data()
        
        total_revenue = 0.0
        total_impressions = 0
        
        # Build and send request
        headers = self._get_auth_headers()
        payload = self._build_report_payload(start_date, end_date)
        
        try:
            response_data = await self._post_json(
                f"{self.BASE_URL}{self.REPORT_ENDPOINT}",
                headers=headers,
                json=payload
            )
        except Exception as e:
            logger.error(f"{self.get_network_name()} API error: {e}")
            raise Exception(f"{self.get_network_name()} API error: {str(e)}")
        
        # Get data array
        if self.RESPONSE_DATA_KEY:
            data_rows = response_data.get(self.RESPONSE_DATA_KEY, [])
        else:
            data_rows = response_data if isinstance(response_data, list) else []
        
        logger.debug(f"Received {len(data_rows)} rows from {self.get_network_name()}")
        
        # Process rows
        for row in data_rows:
            # Extract raw values
            platform_raw = row.get(self.PLATFORM_FIELD, '')
            ad_type_raw = row.get(self.AD_TYPE_FIELD, '')
            revenue_raw = row.get(self.REVENUE_FIELD, 0)
            impressions_raw = row.get(self.IMPRESSIONS_FIELD, 0)
            
            # Map to enums using class mappings or base class helpers
            platform = self.PLATFORM_MAP.get(platform_raw)
            if not platform:
                platform = self._normalize_platform(platform_raw)
            
            ad_type = self.AD_TYPE_MAP.get(ad_type_raw)
            if not ad_type:
                ad_type = self._normalize_ad_type(ad_type_raw)
            
            # Scale revenue
            revenue = float(revenue_raw) / self.REVENUE_SCALE if revenue_raw else 0.0
            impressions = int(impressions_raw) if impressions_raw else 0
            
            # Accumulate totals
            total_revenue += revenue
            total_impressions += impressions
            
            # Use base class helper to accumulate metrics
            self._accumulate_metrics(
                platform_data, ad_data,
                platform, ad_type,
                revenue, impressions
            )
        
        # Build result using base class helper
        result = self._build_result(
            start_date, end_date,
            revenue=total_revenue,
            impressions=total_impressions,
            ad_data=ad_data,
            platform_data=platform_data
        )
        
        # Finalize eCPM calculations
        self._finalize_ecpm(result, ad_data, platform_data)
        
        logger.info(f"{self.get_network_name()}: ${result['revenue']:.2f} revenue, {result['impressions']:,} impressions")
        
        return result
    
    def get_network_name(self) -> str:
        """Return the display name of the network."""
        return NetworkName.NETWORKNAME.display_name  # UPDATE THIS
    
    def get_network_enum(self) -> NetworkName:
        """Return the NetworkName enum."""
        return NetworkName.NETWORKNAME  # UPDATE THIS
