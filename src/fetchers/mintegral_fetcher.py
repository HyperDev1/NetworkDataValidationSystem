"""
Mintegral data fetcher implementation.
Async version using aiohttp with retry support.
"""
import hashlib
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from .base_fetcher import NetworkDataFetcher, FetchResult
from ..enums import Platform, AdType, NetworkName


logger = logging.getLogger(__name__)


class MintegralFetcher(NetworkDataFetcher):
    """Fetcher for Mintegral network data."""
    
    BASE_URL = "https://api.mintegral.com/reporting/data"
    
    # Ad format mapping - Mintegral ad_format values to AdType enum
    AD_TYPE_MAP = {
        'rewarded_video': AdType.REWARDED,
        'interstitial_video': AdType.INTERSTITIAL,
        'sdk_banner': AdType.BANNER,
    }
    
    def __init__(
        self,
        skey: str,
        secret: str,
        app_id: Optional[str] = None
    ):
        """
        Initialize Mintegral fetcher.
        
        Args:
            skey: Mintegral API skey
            secret: Mintegral API secret
            app_id: Optional app ID to filter (comma-separated for multiple apps)
        """
        super().__init__()
        self.skey = skey
        self.secret = secret
        self.app_id = app_id
    
    def _generate_sign(self, timestamp: int) -> str:
        """
        Generate MD5 signature for API authentication.
        sign = md5(SECRET + md5(time))
        """
        time_md5 = hashlib.md5(str(timestamp).encode()).hexdigest()
        return hashlib.md5((self.secret + time_md5).encode()).hexdigest()
    
    async def _make_request(
        self,
        start_date: datetime,
        end_date: datetime,
        ad_format: Optional[str] = None
    ) -> Dict:
        """Make a single request to Mintegral API."""
        timestamp = int(time.time())
        sign = self._generate_sign(timestamp)
        
        params = {
            "skey": self.skey,
            "sign": sign,
            "time": timestamp,
            "start": start_date.strftime("%Y%m%d"),
            "end": end_date.strftime("%Y%m%d"),
            "group_by": "platform",
            "timezone": 0,
        }
        
        if self.app_id:
            params["app_id"] = self.app_id
        
        if ad_format:
            params["ad_format"] = ad_format
        
        return await self._get_json(self.BASE_URL, params=params)
    
    async def fetch_data(self, start_date: datetime, end_date: datetime) -> FetchResult:
        """
        Fetch data from Mintegral Reporting API grouped by ad type and platform.
        Makes separate requests for each ad_format since API doesn't return ad_format in response.
        """
        # Initialize data structures using base class helpers
        ad_data = self._init_ad_data()
        platform_data = self._init_platform_data()
        
        total_revenue = 0.0
        total_impressions = 0
        
        try:
            # Make separate request for each ad_format
            for mintegral_format, ad_type in self.AD_TYPE_MAP.items():
                try:
                    data = await self._make_request(start_date, end_date, mintegral_format)
                    
                    if str(data.get('code', '')).lower() != 'ok':
                        logger.debug(f"Mintegral {mintegral_format}: {data.get('code')}")
                        continue
                    
                    rows = data.get('data', {}).get('lists', [])
                    
                    for row in rows:
                        revenue = float(row.get('est_revenue', 0) or 0)
                        impressions = int(row.get('impression', 0) or 0)
                        
                        # Detect platform using enum
                        plat_val = str(row.get('platform', '')).lower()
                        platform = Platform.IOS if plat_val == 'ios' else Platform.ANDROID
                        
                        # Accumulate totals
                        total_revenue += revenue
                        total_impressions += impressions
                        
                        # Use base class helper to accumulate metrics
                        self._accumulate_metrics(
                            platform_data, ad_data,
                            platform, ad_type,
                            revenue, impressions
                        )
                        
                except Exception as e:
                    logger.warning(f"Mintegral {mintegral_format} error: {str(e)}")
                    continue
            
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
            logger.error(f"Failed to fetch data from Mintegral: {str(e)}")
            raise Exception(f"Failed to fetch data from Mintegral: {str(e)}")
    
    def get_network_name(self) -> str:
        """Return the network name."""
        return NetworkName.MINTEGRAL.display_name
    
    def get_network_enum(self) -> NetworkName:
        """Return the NetworkName enum."""
        return NetworkName.MINTEGRAL

