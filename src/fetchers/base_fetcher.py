"""
Base fetcher interface for network data retrieval.
Provides common methods and async support for all network fetchers.
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any, Optional, TypedDict
from dataclasses import dataclass, field

import aiohttp
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from ..enums import Platform, AdType, NetworkName


logger = logging.getLogger(__name__)


class AdMetrics(TypedDict):
    """Type definition for ad metrics data."""
    revenue: float
    impressions: int
    ecpm: float


class PlatformMetrics(TypedDict):
    """Type definition for platform metrics data."""
    ad_data: Dict[str, AdMetrics]
    revenue: float
    impressions: int
    ecpm: float


class FetchResult(TypedDict):
    """Type definition for fetch result."""
    revenue: float
    impressions: int
    ecpm: float
    network: str
    ad_data: Dict[str, AdMetrics]
    platform_data: Dict[str, PlatformMetrics]
    date_range: Dict[str, str]


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    min_wait: float = 1.0
    max_wait: float = 10.0
    exponential_base: float = 2.0


class NetworkDataFetcher(ABC):
    """
    Abstract base class for network data fetchers.
    
    Provides:
    - Common data structure initialization
    - eCPM calculation
    - Platform and ad type normalization
    - Async HTTP client with retry support
    - Result building helpers
    """
    
    # Override in subclass for network-specific mappings
    PLATFORM_MAP: Dict[str, Platform] = {}
    AD_TYPE_MAP: Dict[str, AdType] = {}
    
    # Default retry configuration
    DEFAULT_RETRY_CONFIG = RetryConfig()
    
    # HTTP timeout settings
    DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=60, connect=10)
    
    def __init__(self, retry_config: Optional[RetryConfig] = None):
        """
        Initialize base fetcher.
        
        Args:
            retry_config: Optional retry configuration
        """
        self.retry_config = retry_config or self.DEFAULT_RETRY_CONFIG
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry - create session."""
        await self._get_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close session."""
        await self.close()
    
    async def close(self):
        """Close the HTTP session if open."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    # =========================================================================
    # Abstract Methods - Must be implemented by subclasses
    # =========================================================================
    
    @abstractmethod
    async def fetch_data(self, start_date: datetime, end_date: datetime) -> FetchResult:
        """
        Fetch revenue and impression data for the given date range.
        
        Args:
            start_date: Start date for data fetch
            end_date: End date for data fetch
            
        Returns:
            FetchResult containing revenue, impressions, and detailed breakdowns
        """
        pass
    
    @abstractmethod
    def get_network_name(self) -> str:
        """Return the name of the network."""
        pass
    
    def get_network_enum(self) -> Optional[NetworkName]:
        """Return the NetworkName enum for this fetcher."""
        return NetworkName.from_api_name(self.get_network_name())
    
    # =========================================================================
    # Data Structure Initialization
    # =========================================================================
    
    def _init_ad_data(self) -> Dict[str, AdMetrics]:
        """
        Initialize empty ad data structure for all ad types.
        
        Returns:
            Dictionary with banner, interstitial, rewarded keys
        """
        return {
            ad_type.value: {'revenue': 0.0, 'impressions': 0, 'ecpm': 0.0}
            for ad_type in AdType
        }
    
    def _init_platform_data(self) -> Dict[str, PlatformMetrics]:
        """
        Initialize empty platform data structure.
        
        Returns:
            Dictionary with android and ios platform data
        """
        return {
            platform.value: {
                'ad_data': self._init_ad_data(),
                'revenue': 0.0,
                'impressions': 0,
                'ecpm': 0.0
            }
            for platform in Platform
        }
    
    # =========================================================================
    # eCPM Calculation
    # =========================================================================
    
    @staticmethod
    def _calculate_ecpm(revenue: float, impressions: int) -> float:
        """
        Calculate eCPM from revenue and impressions.
        
        Args:
            revenue: Revenue in dollars
            impressions: Number of impressions
            
        Returns:
            eCPM value rounded to 2 decimal places
        """
        if impressions <= 0:
            return 0.0
        return round((revenue / impressions) * 1000, 2)
    
    def _finalize_ecpm(
        self,
        result: Dict[str, Any],
        ad_data: Optional[Dict[str, AdMetrics]] = None,
        platform_data: Optional[Dict[str, PlatformMetrics]] = None
    ) -> None:
        """
        Calculate and update eCPM values in data structures.
        
        Args:
            result: Main result dictionary to update
            ad_data: Optional ad data dictionary
            platform_data: Optional platform data dictionary
        """
        # Calculate ad-level eCPM
        if ad_data:
            for ad_type in ad_data:
                metrics = ad_data[ad_type]
                metrics['ecpm'] = self._calculate_ecpm(
                    metrics['revenue'],
                    metrics['impressions']
                )
                metrics['revenue'] = round(metrics['revenue'], 2)
        
        # Calculate platform-level eCPM
        if platform_data:
            for platform in platform_data:
                plat_metrics = platform_data[platform]
                plat_metrics['ecpm'] = self._calculate_ecpm(
                    plat_metrics['revenue'],
                    plat_metrics['impressions']
                )
                plat_metrics['revenue'] = round(plat_metrics['revenue'], 2)
                
                # Also calculate per-platform ad eCPM
                for ad_type in plat_metrics.get('ad_data', {}):
                    ad_metrics = plat_metrics['ad_data'][ad_type]
                    ad_metrics['ecpm'] = self._calculate_ecpm(
                        ad_metrics['revenue'],
                        ad_metrics['impressions']
                    )
                    ad_metrics['revenue'] = round(ad_metrics['revenue'], 2)
        
        # Calculate total eCPM
        result['ecpm'] = self._calculate_ecpm(
            result.get('revenue', 0),
            result.get('impressions', 0)
        )
        result['revenue'] = round(result.get('revenue', 0), 2)
    
    # =========================================================================
    # Normalization Helpers
    # =========================================================================
    
    def _normalize_platform(self, platform: str) -> Platform:
        """
        Normalize platform string to Platform enum.
        
        Uses class-level PLATFORM_MAP first, then falls back to enum conversion.
        
        Args:
            platform: Platform string from API
            
        Returns:
            Platform enum value
        """
        if not platform:
            return Platform.ANDROID
        
        # Check class-specific mapping first
        if self.PLATFORM_MAP:
            mapped = self.PLATFORM_MAP.get(platform)
            if mapped:
                return mapped
            mapped = self.PLATFORM_MAP.get(platform.lower())
            if mapped:
                return mapped
        
        # Fall back to enum's from_string
        return Platform.from_string(platform)
    
    def _normalize_ad_type(self, ad_type: str, incentivized: Optional[bool] = None) -> AdType:
        """
        Normalize ad type string to AdType enum.
        
        Uses class-level AD_TYPE_MAP first, then falls back to enum conversion.
        
        Args:
            ad_type: Ad type string from API
            incentivized: Optional flag for Liftoff video distinction
            
        Returns:
            AdType enum value
        """
        if not ad_type:
            return AdType.INTERSTITIAL
        
        # Check class-specific mapping first
        if self.AD_TYPE_MAP:
            mapped = self.AD_TYPE_MAP.get(ad_type)
            if mapped:
                return mapped
            mapped = self.AD_TYPE_MAP.get(ad_type.lower())
            if mapped:
                return mapped
        
        # Fall back to enum's from_string
        return AdType.from_string(ad_type, incentivized)
    
    # =========================================================================
    # Result Building
    # =========================================================================
    
    def _build_result(
        self,
        start_date: datetime,
        end_date: datetime,
        revenue: float = 0.0,
        impressions: int = 0,
        ad_data: Optional[Dict[str, AdMetrics]] = None,
        platform_data: Optional[Dict[str, PlatformMetrics]] = None,
        **extra_fields
    ) -> FetchResult:
        """
        Build standardized result dictionary.
        
        Args:
            start_date: Report start date
            end_date: Report end date
            revenue: Total revenue
            impressions: Total impressions
            ad_data: Optional ad type breakdown
            platform_data: Optional platform breakdown
            **extra_fields: Additional fields to include
            
        Returns:
            Standardized FetchResult dictionary
        """
        result = {
            'revenue': round(revenue, 2),
            'impressions': impressions,
            'ecpm': self._calculate_ecpm(revenue, impressions),
            'network': self.get_network_name(),
            'ad_data': ad_data or self._init_ad_data(),
            'platform_data': platform_data or self._init_platform_data(),
            'date_range': {
                'start': start_date.strftime("%Y-%m-%d"),
                'end': end_date.strftime("%Y-%m-%d")
            },
            **extra_fields
        }
        return result
    
    # =========================================================================
    # Async HTTP Client with Retry
    # =========================================================================
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.DEFAULT_TIMEOUT)
        return self._session
    
    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def _request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> aiohttp.ClientResponse:
        """
        Make HTTP request with retry support.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional arguments for aiohttp request
            
        Returns:
            aiohttp ClientResponse
        """
        session = await self._get_session()
        
        @retry(
            stop=stop_after_attempt(self.retry_config.max_attempts),
            wait=wait_exponential(
                multiplier=self.retry_config.min_wait,
                max=self.retry_config.max_wait
            ),
            retry=retry_if_exception_type((
                aiohttp.ClientError,
                asyncio.TimeoutError,
            )),
            before_sleep=before_sleep_log(logger, logging.WARNING)
        )
        async def _do_request():
            async with session.request(method, url, **kwargs) as response:
                # Read response body before context exit
                body = await response.read()
                # Check for rate limiting
                if response.status == 429:
                    retry_after = response.headers.get('Retry-After', '60')
                    logger.warning(f"Rate limited. Retry after {retry_after}s")
                    raise aiohttp.ClientResponseError(
                        response.request_info,
                        response.history,
                        status=429,
                        message=f"Rate limited. Retry after {retry_after}s"
                    )
                response.raise_for_status()
                # Store body for later access
                response._body = body
                return response
        
        return await _do_request()
    
    async def _get(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make GET request with retry."""
        return await self._request('GET', url, **kwargs)
    
    async def _post(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make POST request with retry."""
        return await self._request('POST', url, **kwargs)
    
    async def _get_json(self, url: str, **kwargs) -> Any:
        """Make GET request and return JSON response."""
        response = await self._get(url, **kwargs)
        import json
        return json.loads(response._body)
    
    async def _post_json(self, url: str, **kwargs) -> Any:
        """Make POST request and return JSON response."""
        response = await self._post(url, **kwargs)
        import json
        return json.loads(response._body)
    
    # =========================================================================
    # Accumulation Helpers
    # =========================================================================
    
    def _accumulate_metrics(
        self,
        platform_data: Dict[str, PlatformMetrics],
        ad_data: Dict[str, AdMetrics],
        platform: Platform,
        ad_type: AdType,
        revenue: float,
        impressions: int
    ) -> None:
        """
        Accumulate metrics into platform and ad data structures.
        
        Args:
            platform_data: Platform data dict to update
            ad_data: Ad data dict to update
            platform: Platform enum
            ad_type: AdType enum
            revenue: Revenue to add
            impressions: Impressions to add
        """
        plat_key = platform.value
        ad_key = ad_type.value
        
        # Accumulate ad-level totals
        ad_data[ad_key]['revenue'] += revenue
        ad_data[ad_key]['impressions'] += impressions
        
        # Accumulate platform-level totals
        platform_data[plat_key]['revenue'] += revenue
        platform_data[plat_key]['impressions'] += impressions
        
        # Accumulate platform-ad combination
        platform_data[plat_key]['ad_data'][ad_key]['revenue'] += revenue
        platform_data[plat_key]['ad_data'][ad_key]['impressions'] += impressions
    
    # =========================================================================
    # Context Manager Support
    # =========================================================================
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close session."""
        await self.close()
        return False
