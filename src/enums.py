"""
Enums for Network Data Validation System.
Provides type-safe constants for platforms, ad types, and network names.
"""
from enum import Enum
from typing import Optional


class Platform(str, Enum):
    """Platform identifiers for ad networks."""
    ANDROID = "android"
    IOS = "ios"
    
    @classmethod
    def from_string(cls, value: str) -> "Platform":
        """
        Convert various string representations to Platform enum.
        
        Args:
            value: Platform string from any API (e.g., 'Android', 'ANDROID', 'ios', etc.)
            
        Returns:
            Platform enum value
        """
        if not value:
            return cls.ANDROID
            
        mapping = {
            # Android variations
            'android': cls.ANDROID,
            'Android': cls.ANDROID,
            'ANDROID': cls.ANDROID,
            'PLATFORM_TYPE_ANDROID': cls.ANDROID,
            'google': cls.ANDROID,
            'Google': cls.ANDROID,
            'GOOGLE': cls.ANDROID,
            # iOS variations
            'ios': cls.IOS,
            'iOS': cls.IOS,
            'IOS': cls.IOS,
            'PLATFORM_TYPE_IOS': cls.IOS,
            'apple': cls.IOS,
            'Apple': cls.IOS,
            'APPLE': cls.IOS,
            'iphone': cls.IOS,
            'iPhone': cls.IOS,
            'IPHONE': cls.IOS,
        }
        return mapping.get(value, mapping.get(value.lower(), cls.ANDROID))
    
    @property
    def display_name(self) -> str:
        """Return human-readable display name."""
        return self.value.capitalize() if self == Platform.ANDROID else "iOS"


class AdType(str, Enum):
    """Ad format types."""
    BANNER = "banner"
    INTERSTITIAL = "interstitial"
    REWARDED = "rewarded"
    
    @classmethod
    def from_string(cls, value: str, incentivized: Optional[bool] = None) -> "AdType":
        """
        Convert various string representations to AdType enum.
        
        Args:
            value: Ad type string from any API
            incentivized: Optional flag for Liftoff video type distinction
            
        Returns:
            AdType enum value
        """
        if not value:
            return cls.INTERSTITIAL
            
        value_clean = value.strip()
        value_lower = value_clean.lower()
        
        # Banner variations
        banner_values = {
            'banner', 'sdk_banner', 'native', 'native_banner',
            'medium_rectangle', 'mrec', 'adaptive_banner',
            'leaderboard', 'large_banner', 'smart_banner',
        }
        
        # Interstitial variations
        interstitial_values = {
            'interstitial', 'interstitial_video', 'fullscreen',
            'non_skippable_interstitial', 'app_open', 'appopen',
            'static_interstitial', 'video_interstitial',
        }
        
        # Rewarded variations
        rewarded_values = {
            'rewarded', 'rewarded_video', 'rewardedvideo',
            'rewarded_interstitial', 'reward_video',
            'fullscreen_rewarded', 'skippable_video', 'non_skippable_video',
            'incentivized', 'incentivized_video',
        }
        
        # Special case for Liftoff video with incentivized flag
        if value_lower == 'video':
            return cls.REWARDED if incentivized else cls.INTERSTITIAL
        
        if value_lower in banner_values:
            return cls.BANNER
        elif value_lower in interstitial_values:
            return cls.INTERSTITIAL
        elif value_lower in rewarded_values:
            return cls.REWARDED
        
        # Check with underscores removed
        value_no_underscore = value_lower.replace('_', '').replace(' ', '')
        if value_no_underscore in {'rewardedvideo', 'rewardvideo'}:
            return cls.REWARDED
        if value_no_underscore in {'interstitialvideo', 'videointerstitial'}:
            return cls.INTERSTITIAL
            
        # Default fallback
        return cls.INTERSTITIAL
    
    @property
    def display_name(self) -> str:
        """Return human-readable display name."""
        return self.value.capitalize()


class NetworkName(str, Enum):
    """Ad network identifiers."""
    MINTEGRAL = "mintegral"
    UNITY = "unity"
    ADMOB = "admob"
    IRONSOURCE = "ironsource"
    META = "meta"
    MOLOCO = "moloco"
    INMOBI = "inmobi"
    BIDMACHINE = "bidmachine"
    LIFTOFF = "liftoff"
    DT_EXCHANGE = "dt_exchange"
    PANGLE = "pangle"
    APPLOVIN = "applovin"
    APPLOVIN_EXCHANGE = "applovin_exchange"
    CHARTBOOST = "chartboost"
    
    @property
    def icon(self) -> str:
        """Return Slack emoji icon for network."""
        icon_map = {
            NetworkName.MINTEGRAL: ":mintegral:",
            NetworkName.UNITY: ":unity:",
            NetworkName.ADMOB: ":google:",
            NetworkName.IRONSOURCE: ":ironsource:",
            NetworkName.META: ":meta:",
            NetworkName.MOLOCO: ":moloco:",
            NetworkName.INMOBI: ":inmobi:",
            NetworkName.BIDMACHINE: ":bidmachine:",
            NetworkName.LIFTOFF: ":liftoff:",
            NetworkName.DT_EXCHANGE: ":dt_exchange:",
            NetworkName.PANGLE: ":pangle:",
            NetworkName.APPLOVIN: ":applovin:",
            NetworkName.APPLOVIN_EXCHANGE: ":applovin:",
            NetworkName.CHARTBOOST: ":chartboost:",
        }
        return icon_map.get(self, ":chart_with_upwards_trend:")
    
    @property
    def data_delay_days(self) -> int:
        """Return typical data availability delay in days for this network."""
        delay_map = {
            NetworkName.META: 2,  # Meta has 48h delay
            NetworkName.PANGLE: 2,  # Pangle has delay
            # DT Exchange: Try T-1, empty days filtered (last report date may be T-2)
        }
        return delay_map.get(self, 1)  # Default 1 day delay
    
    @property
    def supports_fallback(self) -> bool:
        """Return whether network supports fallback to previous day data."""
        # Networks known to have occasional API issues
        fallback_networks = {
            NetworkName.BIDMACHINE,
            NetworkName.LIFTOFF,
            NetworkName.META,
        }
        return self in fallback_networks
    
    @property
    def display_name(self) -> str:
        """Return human-readable display name for Slack/reports."""
        display_map = {
            NetworkName.MINTEGRAL: "Mintegral Bidding",
            NetworkName.UNITY: "Unity Bidding",
            NetworkName.ADMOB: "Google Bidding",
            NetworkName.IRONSOURCE: "Ironsource Bidding",
            NetworkName.META: "Meta Bidding",
            NetworkName.MOLOCO: "Moloco Bidding",
            NetworkName.INMOBI: "Inmobi Bidding",
            NetworkName.BIDMACHINE: "Bidmachine Bidding",
            NetworkName.LIFTOFF: "Liftoff Bidding",
            NetworkName.DT_EXCHANGE: "DT Exchange Bidding",
            NetworkName.PANGLE: "Pangle Bidding",
            NetworkName.APPLOVIN: "Applovin Bidding",
            NetworkName.APPLOVIN_EXCHANGE: "Applovin Exchange",
            NetworkName.CHARTBOOST: "Chartboost Bidding",
        }
        return display_map.get(self, self.value.replace('_', ' ').title())
    
    @classmethod
    def from_api_name(cls, api_name: str) -> Optional["NetworkName"]:
        """
        Convert API network name to enum.
        
        Args:
            api_name: Network name from any API (AppLovin, etc.)
            
        Returns:
            NetworkName enum or None if not recognized
        """
        if not api_name:
            return None
            
        # Comprehensive mapping of all known API name variations
        mapping = {
            # Mintegral
            'MINTEGRAL_BIDDING': cls.MINTEGRAL,
            'MINTEGRAL': cls.MINTEGRAL,
            'Mintegral Bidding': cls.MINTEGRAL,
            'Mintegral': cls.MINTEGRAL,
            'mintegral': cls.MINTEGRAL,
            # Unity
            'UNITY_BIDDING': cls.UNITY,
            'UNITY': cls.UNITY,
            'Unity Bidding': cls.UNITY,
            'Unity': cls.UNITY,
            'unity': cls.UNITY,
            # AdMob/Google
            'ADMOB_BIDDING': cls.ADMOB,
            'ADMOB': cls.ADMOB,
            'GOOGLE_BIDDING': cls.ADMOB,
            'GOOGLE': cls.ADMOB,
            'Google Bidding': cls.ADMOB,
            'Google': cls.ADMOB,
            'AdMob Bidding': cls.ADMOB,
            'AdMob': cls.ADMOB,
            'admob': cls.ADMOB,
            'google': cls.ADMOB,
            # IronSource
            'IRONSOURCE_BIDDING': cls.IRONSOURCE,
            'IRONSOURCE': cls.IRONSOURCE,
            'ironSource Bidding': cls.IRONSOURCE,
            'ironSource': cls.IRONSOURCE,
            'IronSource Bidding': cls.IRONSOURCE,
            'IronSource': cls.IRONSOURCE,
            'Ironsource Bidding': cls.IRONSOURCE,  # AppLovin MAX format
            'Ironsource': cls.IRONSOURCE,
            'ironsource': cls.IRONSOURCE,
            # Meta/Facebook
            'FACEBOOK_NETWORK': cls.META,
            'FACEBOOK_BIDDING': cls.META,
            'FACEBOOK': cls.META,
            'META_AUDIENCE_NETWORK': cls.META,
            'META_BIDDING': cls.META,
            'META': cls.META,
            'Facebook Bidding': cls.META,
            'Facebook': cls.META,
            'Meta Bidding': cls.META,
            'Meta': cls.META,
            'meta': cls.META,
            'facebook': cls.META,
            # Moloco
            'MOLOCO_BIDDING': cls.MOLOCO,
            'MOLOCO': cls.MOLOCO,
            'Moloco Bidding': cls.MOLOCO,
            'Moloco': cls.MOLOCO,
            'moloco': cls.MOLOCO,
            # InMobi
            'INMOBI_BIDDING': cls.INMOBI,
            'INMOBI': cls.INMOBI,
            'InMobi Bidding': cls.INMOBI,
            'InMobi': cls.INMOBI,
            'Inmobi Bidding': cls.INMOBI,  # AppLovin MAX format
            'Inmobi': cls.INMOBI,
            'inmobi': cls.INMOBI,
            # BidMachine
            'BIDMACHINE_BIDDING': cls.BIDMACHINE,
            'BIDMACHINE': cls.BIDMACHINE,
            'BidMachine Bidding': cls.BIDMACHINE,
            'BidMachine': cls.BIDMACHINE,
            'Bidmachine Bidding': cls.BIDMACHINE,  # AppLovin MAX format
            'Bidmachine': cls.BIDMACHINE,
            'bidmachine': cls.BIDMACHINE,
            # Liftoff/Vungle
            'LIFTOFF_BIDDING': cls.LIFTOFF,
            'LIFTOFF': cls.LIFTOFF,
            'VUNGLE_BIDDING': cls.LIFTOFF,
            'VUNGLE': cls.LIFTOFF,
            'Liftoff Bidding': cls.LIFTOFF,
            'Liftoff': cls.LIFTOFF,
            'Vungle Bidding': cls.LIFTOFF,
            'Vungle': cls.LIFTOFF,
            'liftoff': cls.LIFTOFF,
            'vungle': cls.LIFTOFF,
            # DT Exchange/Fyber
            'DT_EXCHANGE_BIDDING': cls.DT_EXCHANGE,
            'DT_EXCHANGE': cls.DT_EXCHANGE,
            'FYBER_BIDDING': cls.DT_EXCHANGE,
            'FYBER': cls.DT_EXCHANGE,
            'DT Exchange Bidding': cls.DT_EXCHANGE,
            'DT Exchange': cls.DT_EXCHANGE,
            'Fyber Bidding': cls.DT_EXCHANGE,
            'Fyber': cls.DT_EXCHANGE,
            'dt_exchange': cls.DT_EXCHANGE,
            'fyber': cls.DT_EXCHANGE,
            # Pangle/TikTok
            'PANGLE_BIDDING': cls.PANGLE,
            'PANGLE': cls.PANGLE,
            'Pangle Bidding': cls.PANGLE,
            'Pangle': cls.PANGLE,
            'TIKTOK_BIDDING': cls.PANGLE,
            'TIKTOK': cls.PANGLE,
            'TikTok Bidding': cls.PANGLE,
            'TikTok': cls.PANGLE,
            'Tiktok Bidding': cls.PANGLE,
            'Tiktok': cls.PANGLE,
            'pangle': cls.PANGLE,
            'tiktok': cls.PANGLE,
            # AppLovin
            'APPLOVIN_BIDDING': cls.APPLOVIN,
            'APPLOVIN': cls.APPLOVIN,
            'AppLovin Bidding': cls.APPLOVIN,
            'AppLovin': cls.APPLOVIN,
            'applovin': cls.APPLOVIN,
            # AppLovin Exchange
            'APPLOVIN_EXCHANGE': cls.APPLOVIN_EXCHANGE,
            'ALX': cls.APPLOVIN_EXCHANGE,
            'AppLovin Exchange': cls.APPLOVIN_EXCHANGE,
            'applovin_exchange': cls.APPLOVIN_EXCHANGE,
            # Chartboost
            'CHARTBOOST_BIDDING': cls.CHARTBOOST,
            'CHARTBOOST': cls.CHARTBOOST,
            'Chartboost Bidding': cls.CHARTBOOST,
            'Chartboost': cls.CHARTBOOST,
            'chartboost': cls.CHARTBOOST,
        }
        return mapping.get(api_name)
    
    @classmethod
    def get_all_api_names(cls, network: "NetworkName") -> list:
        """
        Get all known API name variations for a network.
        
        Args:
            network: NetworkName enum value
            
        Returns:
            List of all API name strings that map to this network
        """
        api_names = {
            cls.MINTEGRAL: ['MINTEGRAL_BIDDING', 'MINTEGRAL', 'Mintegral Bidding', 'Mintegral'],
            cls.UNITY: ['UNITY_BIDDING', 'UNITY', 'Unity Bidding', 'Unity'],
            cls.ADMOB: ['ADMOB_BIDDING', 'ADMOB', 'GOOGLE_BIDDING', 'GOOGLE', 'Google Bidding', 'Google', 'AdMob Bidding', 'AdMob'],
            cls.IRONSOURCE: ['IRONSOURCE_BIDDING', 'IRONSOURCE', 'ironSource Bidding', 'ironSource', 'IronSource Bidding', 'IronSource'],
            cls.META: ['FACEBOOK_NETWORK', 'FACEBOOK_BIDDING', 'FACEBOOK', 'META_AUDIENCE_NETWORK', 'META_BIDDING', 'META', 'Facebook Bidding', 'Facebook', 'Meta Bidding', 'Meta'],
            cls.MOLOCO: ['MOLOCO_BIDDING', 'MOLOCO', 'Moloco Bidding', 'Moloco'],
            cls.INMOBI: ['INMOBI_BIDDING', 'INMOBI', 'InMobi Bidding', 'InMobi'],
            cls.BIDMACHINE: ['BIDMACHINE_BIDDING', 'BIDMACHINE', 'BidMachine Bidding', 'BidMachine'],
            cls.LIFTOFF: ['LIFTOFF_BIDDING', 'LIFTOFF', 'VUNGLE_BIDDING', 'VUNGLE', 'Liftoff Bidding', 'Liftoff', 'Vungle Bidding', 'Vungle'],
            cls.DT_EXCHANGE: ['DT_EXCHANGE_BIDDING', 'DT_EXCHANGE', 'FYBER_BIDDING', 'FYBER', 'DT Exchange Bidding', 'DT Exchange', 'Fyber Bidding', 'Fyber'],
            cls.PANGLE: ['PANGLE_BIDDING', 'PANGLE', 'Pangle Bidding', 'Pangle', 'TIKTOK_BIDDING', 'TIKTOK', 'TikTok Bidding', 'TikTok'],
            cls.APPLOVIN: ['APPLOVIN_BIDDING', 'APPLOVIN', 'AppLovin Bidding', 'AppLovin'],
            cls.APPLOVIN_EXCHANGE: ['APPLOVIN_EXCHANGE', 'ALX', 'AppLovin Exchange'],
            cls.CHARTBOOST: ['CHARTBOOST_BIDDING', 'CHARTBOOST', 'Chartboost Bidding', 'Chartboost'],
        }
        return api_names.get(network, [])
