"""
IronSource API Test Script
Tests the IronSource Monetization Reporting API integration.

Usage:
    python test_ironsource.py
    
Prerequisites:
    1. Configure IronSource credentials in config.yaml:
       - username: Your IronSource login email
       - secret_key: From My Account → Reporting API section
       - android_app_keys: Comma-separated Android app keys
       - ios_app_keys: Comma-separated iOS app keys
    2. Enable the network: enabled: true
"""
import sys
from datetime import datetime, timedelta, timezone

from src.config import Config
from src.fetchers.ironsource_fetcher import IronSourceFetcher


def test_ironsource():
    """Test IronSource API integration."""
    print("=" * 60)
    print("IronSource API Test")
    print("=" * 60)
    
    # Load configuration
    try:
        config = Config()
        ironsource_config = config.get_ironsource_config()
    except FileNotFoundError as e:
        print(f"❌ Config error: {e}")
        return False
    
    # Check if enabled
    if not ironsource_config.get('enabled'):
        print("⚠️  IronSource is disabled in config.yaml")
        print("   Set 'enabled: true' and configure credentials to test")
        return False
    
    # Check credentials
    username = ironsource_config.get('username', '')
    secret_key = ironsource_config.get('secret_key', '')
    android_app_keys = ironsource_config.get('android_app_keys', '')
    ios_app_keys = ironsource_config.get('ios_app_keys', '')
    
    if not username or not secret_key:
        print("❌ Missing credentials in config.yaml")
        print("   Required: username, secret_key")
        return False
    
    if not android_app_keys and not ios_app_keys:
        print("❌ No app keys configured")
        print("   At least one of android_app_keys or ios_app_keys is required")
        return False
    
    print(f"\n📋 Configuration:")
    print(f"   Username: {username[:20]}...")
    print(f"   Secret Key: {secret_key[:10]}...")
    print(f"   Android App Keys: {android_app_keys or '(none)'}")
    print(f"   iOS App Keys: {ios_app_keys or '(none)'}")
    
    # Initialize fetcher
    print(f"\n🔧 Initializing IronSource fetcher...")
    try:
        fetcher = IronSourceFetcher(
            username=username,
            secret_key=secret_key,
            android_app_keys=android_app_keys,
            ios_app_keys=ios_app_keys,
        )
        print("   ✅ Fetcher initialized")
    except Exception as e:
        print(f"   ❌ Initialization failed: {e}")
        return False
    
    # Test date range (yesterday - 2 days delay for data availability)
    now_utc = datetime.now(timezone.utc)
    end_date = now_utc.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    start_date = end_date  # Single day
    
    print(f"\n📅 Fetching data for: {start_date.strftime('%Y-%m-%d')}")
    
    # Fetch data
    try:
        data = fetcher.fetch_data(start_date, end_date)
        print("   ✅ Data fetched successfully")
    except Exception as e:
        print(f"   ❌ Fetch failed: {e}")
        return False
    
    # Display results
    print(f"\n📊 Results:")
    print(f"   Network: {data.get('network')}")
    print(f"   Date Range: {data.get('date_range', {}).get('start')} to {data.get('date_range', {}).get('end')}")
    print(f"\n   💰 Total Revenue: ${data.get('revenue', 0):.2f}")
    print(f"   👁️  Total Impressions: {data.get('impressions', 0):,}")
    print(f"   📈 Total eCPM: ${data.get('ecpm', 0):.2f}")
    print(f"   🖱️  Total Clicks: {data.get('clicks', 0):,}")
    print(f"   📤 Total Requests: {data.get('requests', 0):,}")
    print(f"   📥 Total Fills: {data.get('fills', 0):,}")
    
    # Platform breakdown
    platform_data = data.get('platform_data', {})
    
    for platform in ['android', 'ios']:
        p_data = platform_data.get(platform, {})
        if p_data.get('impressions', 0) > 0 or p_data.get('revenue', 0) > 0:
            print(f"\n   📱 {platform.upper()}:")
            print(f"      Revenue: ${p_data.get('revenue', 0):.2f}")
            print(f"      Impressions: {p_data.get('impressions', 0):,}")
            print(f"      eCPM: ${p_data.get('ecpm', 0):.2f}")
            
            # Ad type breakdown
            ad_data = p_data.get('ad_data', {})
            for ad_type in ['banner', 'interstitial', 'rewarded']:
                ad = ad_data.get(ad_type, {})
                if ad.get('impressions', 0) > 0 or ad.get('revenue', 0) > 0:
                    print(f"      • {ad_type}: ${ad.get('revenue', 0):.2f} / {ad.get('impressions', 0):,} imps")
    
    print(f"\n✅ IronSource API test completed successfully!")
    return True


if __name__ == "__main__":
    success = test_ironsource()
    sys.exit(0 if success else 1)
