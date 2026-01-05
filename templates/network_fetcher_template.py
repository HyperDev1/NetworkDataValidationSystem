"""
[NetworkName] data fetcher implementation.
API Docs: [API_DOCUMENTATION_URL]

PLACEHOLDER TEMPLATE - Replace all [PLACEHOLDERS] with actual values
"""
import json
import requests
from datetime import datetime
from typing import Dict, Any, Optional
from .base_fetcher import NetworkDataFetcher


class NetworkNameFetcher(NetworkDataFetcher):
    """Fetcher for [NetworkName] monetization data."""
    
    # ============================================================
    # API CONFIGURATION - Update based on API documentation
    # ============================================================
    BASE_URL = "https://api.networkname.com"
    AUTH_ENDPOINT = "/v1/auth/tokens"      # Login endpoint (if session-based)
    REPORT_ENDPOINT = "/v1/reports/summary"  # Report endpoint
    
    # ============================================================
    # MAPPING CONSTANTS - Update based on API response values
    # ============================================================
    
    # Platform mapping: API value → standard value
    PLATFORM_MAP = {
        'ANDROID': 'android',
        'IOS': 'ios',
        'android': 'android',
        'ios': 'ios',
        'PLATFORM_TYPE_ANDROID': 'android',
        'PLATFORM_TYPE_IOS': 'ios',
        # Add more mappings based on API response
    }
    
    # Ad type mapping: API value → standard value
    AD_TYPE_MAP = {
        'BANNER': 'banner',
        'INTERSTITIAL': 'interstitial',
        'REWARDED': 'rewarded',
        'REWARDED_VIDEO': 'rewarded',
        'REWARD_VIDEO': 'rewarded',
        'NATIVE': 'banner',
        'MREC': 'banner',
        'APP_OPEN': 'interstitial',
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
        self.api_key = api_key
        self.publisher_id = publisher_id
        self.app_ids = [a.strip() for a in app_ids.split(',') if a.strip()] if app_ids else []
        self._access_token = None  # For session-based auth
    
    # ============================================================
    # DEBUG METHODS - Use these for testing
    # ============================================================
    
    def _test_auth(self) -> bool:
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
        print(f"   Headers: {json.dumps(self._safe_headers(headers), indent=2)}")
        
        try:
            # Adjust based on auth type (GET or POST)
            response = requests.get(
                f"{self.BASE_URL}{self.AUTH_ENDPOINT}",
                headers=headers,
                timeout=30
            )
            
            print(f"\n📥 RESPONSE:")
            print(f"   Status: {response.status_code}")
            
            try:
                response_json = response.json()
                print(f"   Body:\n{json.dumps(response_json, indent=2)}")
            except:
                print(f"   Body (raw): {response.text[:500]}")
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _test_report_request(self, start_date: datetime, end_date: datetime) -> Dict:
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
        print(f"   Headers: {json.dumps(self._safe_headers(headers), indent=2)}")
        print(f"   Payload:\n{json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(
                f"{self.BASE_URL}{self.REPORT_ENDPOINT}",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            print(f"\n📥 RESPONSE:")
            print(f"   Status: {response.status_code}")
            
            try:
                response_json = response.json()
                # Pretty print (truncate if too long)
                response_str = json.dumps(response_json, indent=2)
                if len(response_str) > 3000:
                    print(f"   Body (truncated):\n{response_str[:3000]}...")
                    print(f"\n   [Response truncated - {len(response_str)} chars total]")
                else:
                    print(f"   Body:\n{response_str}")
                return response_json
            except:
                print(f"   Body (raw): {response.text[:1000]}")
                return {}
                
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
    
    def _safe_headers(self, headers: Dict) -> Dict:
        """Return headers with sensitive values masked."""
        return {
            k: '***' if any(s in k.lower() for s in ['auth', 'key', 'token']) else v 
            for k, v in headers.items()
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
    
    def _create_empty_platform_data(self) -> Dict[str, Any]:
        """Create empty platform data structure."""
        return {
            'revenue': 0.0,
            'impressions': 0,
            'ecpm': 0.0,
            'ad_data': {
                'banner': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0},
                'interstitial': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0},
                'rewarded': {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0},
            }
        }
    
    def _calculate_ecpms(self, data: Dict):
        """Calculate all eCPM values."""
        # Grand total
        if data['impressions'] > 0:
            data['ecpm'] = (data['revenue'] / data['impressions']) * 1000
        
        # Per platform and ad type
        for platform in ['android', 'ios']:
            pdata = data['platform_data'][platform]
            if pdata['impressions'] > 0:
                pdata['ecpm'] = (pdata['revenue'] / pdata['impressions']) * 1000
            
            for ad_type in ['banner', 'interstitial', 'rewarded']:
                adata = pdata['ad_data'][ad_type]
                if adata['impressions'] > 0:
                    adata['ecpm'] = (adata['revenue'] / adata['impressions']) * 1000
    
    # ============================================================
    # MAIN METHODS
    # ============================================================
    
    def _parse_response(self, response_data: Dict) -> Dict[str, Any]:
        """Parse API response to standard format."""
        print("\n🔄 PARSING RESPONSE")
        
        # Initialize result structure
        result = {
            'revenue': 0.0,
            'impressions': 0,
            'ecpm': 0.0,
            'network': self.get_network_name(),
            'platform_data': {
                'android': self._create_empty_platform_data(),
                'ios': self._create_empty_platform_data(),
            }
        }
        
        # Get data array
        if self.RESPONSE_DATA_KEY:
            data_rows = response_data.get(self.RESPONSE_DATA_KEY, [])
        else:
            data_rows = response_data if isinstance(response_data, list) else []
        
        print(f"   Found {len(data_rows)} rows to process")
        
        # Track unique values for debugging
        unique_platforms = set()
        unique_ad_types = set()
        
        for i, row in enumerate(data_rows):
            # Extract raw values
            platform_raw = row.get(self.PLATFORM_FIELD, '')
            ad_type_raw = row.get(self.AD_TYPE_FIELD, '')
            revenue_raw = row.get(self.REVENUE_FIELD, 0)
            impressions_raw = row.get(self.IMPRESSIONS_FIELD, 0)
            
            # Track unique values
            unique_platforms.add(platform_raw)
            unique_ad_types.add(ad_type_raw)
            
            # Map to standard values
            platform = self.PLATFORM_MAP.get(platform_raw)
            if not platform and platform_raw:
                platform = platform_raw.lower()
            
            ad_type = self.AD_TYPE_MAP.get(ad_type_raw)
            if not ad_type and ad_type_raw:
                ad_type = ad_type_raw.lower()
            
            # Scale revenue
            revenue = float(revenue_raw) / self.REVENUE_SCALE if revenue_raw else 0.0
            impressions = int(impressions_raw) if impressions_raw else 0
            
            # Debug first few rows
            if i < 5:
                print(f"\n   Row {i+1}:")
                print(f"      Platform: '{platform_raw}' → '{platform}'")
                print(f"      Ad Type: '{ad_type_raw}' → '{ad_type}'")
                print(f"      Revenue: {revenue_raw} → ${revenue:.4f}")
                print(f"      Impressions: {impressions:,}")
            
            # Validate platform
            if platform not in ['android', 'ios']:
                if i < 5:
                    print(f"      ⚠️ Skipping unknown platform")
                continue
            
            # Validate ad type
            if ad_type not in ['banner', 'interstitial', 'rewarded']:
                if i < 5:
                    print(f"      ⚠️ Skipping unknown ad type")
                continue
            
            # Aggregate
            result['platform_data'][platform]['revenue'] += revenue
            result['platform_data'][platform]['impressions'] += impressions
            result['platform_data'][platform]['ad_data'][ad_type]['revenue'] += revenue
            result['platform_data'][platform]['ad_data'][ad_type]['impressions'] += impressions
            result['revenue'] += revenue
            result['impressions'] += impressions
        
        # Show unique values found (helps with mapping)
        print(f"\n   📋 Unique platforms found: {unique_platforms}")
        print(f"   📋 Unique ad types found: {unique_ad_types}")
        
        # Calculate eCPMs
        self._calculate_ecpms(result)
        
        # Print summary
        print(f"\n📊 AGGREGATION SUMMARY:")
        print(f"   Total Revenue: ${result['revenue']:.2f}")
        print(f"   Total Impressions: {result['impressions']:,}")
        print(f"   Total eCPM: ${result['ecpm']:.2f}")
        
        for platform in ['android', 'ios']:
            pdata = result['platform_data'][platform]
            if pdata['impressions'] > 0:
                print(f"\n   {platform.upper()}: ${pdata['revenue']:.2f} / {pdata['impressions']:,} impr")
                for ad_type, adata in pdata['ad_data'].items():
                    if adata['impressions'] > 0:
                        print(f"      {ad_type}: ${adata['revenue']:.2f} / {adata['impressions']:,} impr")
        
        return result
    
    def fetch_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Fetch revenue and impression data for the given date range.
        
        Args:
            start_date: Start date for data fetch
            end_date: End date for data fetch
            
        Returns:
            Dictionary containing revenue and impressions data
        """
        print(f"\n{'='*60}")
        print(f"📊 {self.get_network_name()} Data Fetch")
        print(f"   Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"{'='*60}")
        
        # Build request
        headers = self._get_auth_headers()
        payload = self._build_report_payload(start_date, end_date)
        
        print(f"\n📤 Request Payload:\n{json.dumps(payload, indent=2)}")
        
        # Make request
        response = requests.post(
            f"{self.BASE_URL}{self.REPORT_ENDPOINT}",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        print(f"\n📥 Response Status: {response.status_code}")
        
        if response.status_code != 200:
            error_text = response.text[:500]
            print(f"   ❌ Error Response:\n{error_text}")
            raise Exception(f"API Error: {response.status_code} - {error_text}")
        
        response_data = response.json()
        
        # Count rows
        if self.RESPONSE_DATA_KEY:
            row_count = len(response_data.get(self.RESPONSE_DATA_KEY, []))
        else:
            row_count = len(response_data) if isinstance(response_data, list) else 0
        print(f"   ✅ Received {row_count} rows")
        
        # Parse and return
        result = self._parse_response(response_data)
        result['date_range'] = {
            'start': start_date.strftime('%Y-%m-%d'),
            'end': end_date.strftime('%Y-%m-%d')
        }
        
        return result
    
    def get_network_name(self) -> str:
        """Return the name of the network."""
        return "NetworkName"  # UPDATE THIS
