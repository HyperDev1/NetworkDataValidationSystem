"""
InMobi data fetcher implementation.
Uses InMobi Publisher Reporting API for fetching monetization data.
API Docs: https://support.inmobi.com/monetize/inmobi-apis/reporting-api
"""
import requests
from datetime import datetime
from typing import Dict, Any, Optional
from .base_fetcher import NetworkDataFetcher


class InMobiFetcher(NetworkDataFetcher):
    """Fetcher for InMobi monetization data using Publisher Reporting API."""
    
    # InMobi API URLs
    # Updated based on InMobi team recommendation (v1.0 for session generation)
    SESSION_URL = "https://api.inmobi.com/v1.0/generatesession/generate"
    REPORTING_URL = "https://api.inmobi.com/v3.0/reporting/publisher"
    
    # Ad format mapping - InMobi ad types to our standard categories
    AD_FORMAT_MAP = {
        'banner': 'banner',
        'native': 'banner',
        'interstitial': 'interstitial',
        'rewarded video': 'rewarded',
        'rewarded': 'rewarded',
        'rewardedvideo': 'rewarded',
    }
    
    # Platform mapping
    PLATFORM_MAP = {
        'android': 'android',
        'ios': 'ios',
    }
    
    def __init__(
        self,
        account_id: str,
        secret_key: str,
        username: Optional[str] = None,
        app_ids: Optional[str] = None
    ):
        """
        Initialize InMobi fetcher.
        
        Args:
            account_id: InMobi Account ID (found in InMobi dashboard)
            secret_key: InMobi Secret Key (from Account Settings > API Key)
            username: InMobi login email (used for session generation userName header)
            app_ids: Comma-separated InMobi App IDs to filter (optional)
        """
        self.account_id = account_id
        self.secret_key = secret_key
        self.username = username or account_id  # Use email if provided, otherwise account_id
        self.app_ids = [p.strip() for p in app_ids.split(',') if p.strip()] if app_ids else []
        self.session_id = None
    
    def _generate_session(self) -> str:
        """
        Generate a session ID for API authentication.
        InMobi requires session-based authentication for reporting API.
        
        API Docs: https://support.inmobi.com/monetize/inmobi-apis/reporting-api#generate-session-id
        
        Returns:
            Session ID string
        """
        if self.session_id:
            return self.session_id
        
        # InMobi uses userName and secretKey headers for session generation
        # API Doc: https://support.inmobi.com/monetize/inmobi-apis/reporting-api#generate-session-id
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "userName": self.username,    # Email or Account ID
            "secretKey": self.secret_key  # API Key / Secret Key
        }
        
        print(f"      [INFO] Generating InMobi session...")
        print(f"      [DEBUG] Session URL: {self.SESSION_URL}")
        print(f"      [DEBUG] userName: {self.username}")
        print(f"      [DEBUG] secretKey: {self.secret_key[:20]}...")
        
        try:
            # GET request with credentials in headers (as per InMobi team recommendation)
            response = requests.get(
                self.SESSION_URL,
                headers=headers,
                timeout=30,
                allow_redirects=True  # Follow redirects
            )
            
            print(f"      [DEBUG] Session Response Status: {response.status_code}")
            print(f"      [DEBUG] Session Response URL: {response.url}")
            print(f"      [DEBUG] Session Response: {response.text[:500] if response.text else 'Empty'}")
            
            response.raise_for_status()
            data = response.json()
            
            # Check for error in response
            if data.get("error"):
                error_list = data.get("errorList", []) or data.get("errors", [])
                error_msg = ", ".join([e.get("message", e.get("reason", str(e))) for e in error_list])
                raise ValueError(f"InMobi session error: {error_msg}")
            
            # Get session ID from response
            # Response format: {"respList":[{"sessionId":"...","accountId":"..."}],"error":false}
            resp_list = data.get("respList", [])
            if resp_list and len(resp_list) > 0:
                self.session_id = resp_list[0].get("sessionId")
            else:
                self.session_id = data.get("sessionId")
            
            if not self.session_id:
                raise ValueError(f"Session ID not found in response: {data}")
            
            print(f"      [OK] Session generated: {self.session_id[:20]}...")
            return self.session_id
            
        except requests.exceptions.HTTPError as e:
            print(f"      [ERROR] Session generation HTTP error: {e.response.status_code}")
            print(f"      [ERROR] Response: {e.response.text}")
            raise
        except Exception as e:
            print(f"      [ERROR] Session generation error: {str(e)}")
            raise
    
    def _normalize_platform(self, platform: str) -> str:
        """Normalize platform name to standard format."""
        if not platform:
            return 'android'
        
        platform_lower = platform.lower().strip()
        return self.PLATFORM_MAP.get(platform_lower, 'android')
    
    def _normalize_ad_format(self, ad_format: str) -> str:
        """Normalize ad format to standard category."""
        if not ad_format:
            return 'interstitial'
        
        ad_format_lower = ad_format.lower().strip()
        return self.AD_FORMAT_MAP.get(ad_format_lower, 'interstitial')
    
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
    
    def fetch_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Fetch revenue and impression data from InMobi Publisher Reporting API.
        
        API Documentation: https://support.inmobi.com/monetize/inmobi-apis/reporting-api
        
        Args:
            start_date: Start date for data fetch
            end_date: End date for data fetch
            
        Returns:
            Dictionary containing revenue and impressions data with platform/ad type breakdown
        """
        # Initialize data structure
        platform_data = self._init_platform_data()
        total_revenue = 0.0
        total_impressions = 0
        
        try:
            # Generate session first
            session_id = self._generate_session()
            
            # Prepare API request headers with session
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "accountId": self.account_id,
                "sessionId": session_id,
                "secretKey": self.secret_key  # Required for reporting API
            }
            
            # API request body according to InMobi documentation
            # Ref: https://support.inmobi.com/monetize/inmobi-apis/reporting-api
            # timeFrame format: "yyyy-MM-dd:yyyy-MM-dd" (startDate:endDate)
            time_frame = f"{start_date.strftime('%Y-%m-%d')}:{end_date.strftime('%Y-%m-%d')}"
            
            # Build report request
            report_request = {
                "metrics": [
                    "adImpressions",
                    "earnings"
                ],
                "timeFrame": time_frame,
                "groupBy": [
                    "platform",
                    "adUnitType"
                ]
            }
            
            # Add app filter if specified
            if self.app_ids:
                report_request["filterBy"] = [
                    {
                        "filterName": "inmobiAppId",
                        "filterValue": self.app_ids
                    }
                ]
                print(f"      [INFO] Filtering by InMobi App IDs: {self.app_ids}")
            
            body = {
                "reportRequest": report_request
            }
            
            print(f"      [INFO] Requesting InMobi data for {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            print(f"      [DEBUG] Request body: {body}")
            
            response = requests.post(
                self.REPORTING_URL,
                json=body,
                headers=headers,
                timeout=60
            )
            
            print(f"      [DEBUG] Response Status: {response.status_code}")
            print(f"      [DEBUG] Response: {response.text[:500]}")
            
            response.raise_for_status()
            
            data = response.json()
            
            # Check for error in response
            if data.get("error"):
                error_list = data.get("errorList", [])
                error_msg = ", ".join([e.get("message", str(e)) for e in error_list])
                raise ValueError(f"InMobi API error: {error_msg}")
            
            # Parse response - InMobi returns data in respList
            rows = data.get("respList", [])
            
            print(f"      [INFO] Received {len(rows)} data rows")
            
            for row in rows:
                revenue = float(row.get("earnings", 0) or 0)
                impressions = int(row.get("adImpressions", 0) or 0)
                platform_raw = row.get("platform", "android")
                ad_type_raw = row.get("adUnitType", "interstitial")
                
                print(f"      [DEBUG] Row: platform={platform_raw}, adType={ad_type_raw}, revenue={revenue}, impressions={impressions}")
                
                # Normalize values
                platform = self._normalize_platform(platform_raw)
                ad_type = self._normalize_ad_format(ad_type_raw)
                
                # Accumulate totals
                total_revenue += revenue
                total_impressions += impressions
                
                # Accumulate per-platform
                platform_data[platform]['revenue'] += revenue
                platform_data[platform]['impressions'] += impressions
                
                # Accumulate per ad type
                platform_data[platform]['ad_data'][ad_type]['revenue'] += revenue
                platform_data[platform]['ad_data'][ad_type]['impressions'] += impressions
            
            # Build result
            result = {
                'revenue': round(total_revenue, 2),
                'impressions': total_impressions,
                'ecpm': self._calculate_ecpm(total_revenue, total_impressions),
                'network': self.get_network_name(),
                'date_range': {
                    'start': start_date.strftime('%Y-%m-%d'),
                    'end': end_date.strftime('%Y-%m-%d')
                },
                'platform_data': platform_data
            }
            
            # Calculate all eCPM values
            self._finalize_ecpm(result)
            
            # Round revenue values
            for platform_key in ['android', 'ios']:
                platform = result['platform_data'][platform_key]
                platform['revenue'] = round(platform['revenue'], 2)
                for ad_type in ['banner', 'interstitial', 'rewarded']:
                    platform['ad_data'][ad_type]['revenue'] = round(
                        platform['ad_data'][ad_type]['revenue'], 2
                    )
            
            return result
            
        except requests.exceptions.HTTPError as e:
            print(f"      [ERROR] InMobi API HTTP error: {e.response.status_code}")
            print(f"      [ERROR] Response: {e.response.text}")
            raise
        except Exception as e:
            print(f"      [ERROR] InMobi fetch error: {str(e)}")
            raise
    
    def get_network_name(self) -> str:
        """Return the name of the network."""
        return "InMobi Bidding"

