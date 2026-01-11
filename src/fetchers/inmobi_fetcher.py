"""
InMobi data fetcher implementation.
Async version using aiohttp with retry support.
API Docs: https://support.inmobi.com/monetize/inmobi-apis/reporting-api
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from .base_fetcher import NetworkDataFetcher, FetchResult
from ..enums import Platform, AdType, NetworkName
from ..utils import TokenCache


logger = logging.getLogger(__name__)


class InMobiFetcher(NetworkDataFetcher):
    """Fetcher for InMobi monetization data using Publisher Reporting API."""
    
    # InMobi API URLs
    # Updated based on InMobi team recommendation (v1.0 for session generation)
    SESSION_URL = "https://api.inmobi.com/v1.0/generatesession/generate"
    REPORTING_URL = "https://api.inmobi.com/v3.0/reporting/publisher"
    
    # Token cache key
    TOKEN_CACHE_KEY = "inmobi"
    TOKEN_EXPIRES_IN = 3300  # 55 minutes
    
    # Ad format mapping - InMobi ad types to AdType enum
    AD_FORMAT_MAP = {
        'banner': AdType.BANNER,
        'native': AdType.BANNER,
        'interstitial': AdType.INTERSTITIAL,
        'rewarded video': AdType.REWARDED,
        'rewarded': AdType.REWARDED,
        'rewardedvideo': AdType.REWARDED,
    }
    
    # Platform mapping
    PLATFORM_MAP = {
        'android': Platform.ANDROID,
        'ios': Platform.IOS,
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
        super().__init__()
        self.account_id = account_id
        self.secret_key = secret_key
        self.username = username or account_id  # Use email if provided, otherwise account_id
        self.app_ids = [p.strip() for p in app_ids.split(',') if p.strip()] if app_ids else []
        self._token_cache = TokenCache()
        self._session_id = None
    
    async def _generate_session(self) -> str:
        """
        Generate a session ID for API authentication.
        InMobi requires session-based authentication for reporting API.
        
        Returns:
            Session ID string
        """
        # Check cache first
        cached = self._token_cache.get_token(self.TOKEN_CACHE_KEY)
        if cached:
            logger.debug("Using cached InMobi session")
            return cached['token']
        
        # InMobi uses userName and secretKey headers for session generation
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "userName": self.username,
            "secretKey": self.secret_key
        }
        
        logger.debug(f"Generating InMobi session for user: {self.username}")
        
        try:
            # GET request with credentials in headers
            data = await self._get_json(self.SESSION_URL, headers=headers)
            
            # Check for error in response
            if data.get("error"):
                error_list = data.get("errorList", []) or data.get("errors", [])
                error_msg = ", ".join([e.get("message", e.get("reason", str(e))) for e in error_list])
                raise ValueError(f"InMobi session error: {error_msg}")
            
            # Get session ID from response
            # Response format: {"respList":[{"sessionId":"...","accountId":"..."}],"error":false}
            resp_list = data.get("respList", [])
            if resp_list and len(resp_list) > 0:
                session_id = resp_list[0].get("sessionId")
            else:
                session_id = data.get("sessionId")
            
            if not session_id:
                raise ValueError(f"Session ID not found in response: {data}")
            
            # Cache the session
            self._token_cache.save_token(
                self.TOKEN_CACHE_KEY,
                session_id,
                expires_in=self.TOKEN_EXPIRES_IN
            )
            
            logger.debug(f"InMobi session generated: {session_id[:20]}...")
            return session_id
            
        except Exception as e:
            logger.error(f"InMobi session generation error: {str(e)}")
            raise
    
    async def fetch_data(self, start_date: datetime, end_date: datetime) -> FetchResult:
        """
        Fetch revenue and impression data from InMobi Publisher Reporting API.
        
        Args:
            start_date: Start date for data fetch
            end_date: End date for data fetch
            
        Returns:
            FetchResult containing revenue and impressions data with platform/ad type breakdown
        """
        # Initialize data structures using base class helpers
        ad_data = self._init_ad_data()
        platform_data = self._init_platform_data()
        total_revenue = 0.0
        total_impressions = 0
        
        try:
            # Generate session first
            session_id = await self._generate_session()
            
            # Prepare API request headers with session
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "accountId": self.account_id,
                "sessionId": session_id,
                "secretKey": self.secret_key
            }
            
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
                logger.debug(f"Filtering by InMobi App IDs: {self.app_ids}")
            
            body = {
                "reportRequest": report_request
            }
            
            logger.debug(f"Requesting InMobi data for {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            
            data = await self._post_json(self.REPORTING_URL, headers=headers, json=body)
            
            # Check for error in response
            if data.get("error"):
                error_list = data.get("errorList", [])
                error_msg = ", ".join([e.get("message", str(e)) for e in error_list])
                raise ValueError(f"InMobi API error: {error_msg}")
            
            # Parse response - InMobi returns data in respList
            rows = data.get("respList", [])
            
            logger.debug(f"Received {len(rows)} data rows from InMobi")
            
            for row in rows:
                revenue = float(row.get("earnings", 0) or 0)
                impressions = int(row.get("adImpressions", 0) or 0)
                platform_raw = row.get("platform", "android")
                ad_type_raw = row.get("adUnitType", "interstitial")
                
                # Normalize values
                platform = self._normalize_platform(str(platform_raw).lower())
                ad_type = self._normalize_ad_type(str(ad_type_raw).lower())
                
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
            
            return result
            
        except Exception as e:
            logger.error(f"InMobi fetch error: {str(e)}")
            raise
    
    def get_network_name(self) -> str:
        """Return the name of the network."""
        return NetworkName.INMOBI.display_name
    
    def get_network_enum(self) -> NetworkName:
        """Return the NetworkName enum."""
        return NetworkName.INMOBI

