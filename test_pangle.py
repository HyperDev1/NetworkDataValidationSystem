"""
Pangle API Test Script
Tests the Pangle Reporting API v2 integration.

Usage:
    python test_pangle.py
    
Prerequisites:
    1. Configure Pangle credentials in config.yaml:
       - user_id: Your Pangle account ID
       - role_id: Role ID (found near security key in dashboard)
       - secure_key: From Pangle platform → SDK Integration → Data API
       - time_zone: 0 for UTC, 8 for UTC+8 (optional, default: 0)
       - currency: "usd" or "cny" (optional, default: "usd")
    2. Enable the network: enabled: true
"""
import sys
from datetime import datetime, timedelta, timezone

from src.config import Config
from src.fetchers.pangle_fetcher import PangleFetcher


def test_pangle():
    """Test Pangle API integration."""
    print("=" * 60)
    print("Pangle API Test")
    print("=" * 60)
    
    # Load configuration
    try:
        config = Config()
        pangle_config = config.get_pangle_config()
    except FileNotFoundError as e:
        print(f"❌ Config error: {e}")
        return False
    
    # Check if enabled
    if not pangle_config.get('enabled'):
        print("⚠️  Pangle is disabled in config.yaml")
        print("   Set 'enabled: true' and configure credentials to test")
        return False
    
    # Check credentials
    user_id = pangle_config.get('user_id', '')
    role_id = pangle_config.get('role_id', '')
    secure_key = pangle_config.get('secure_key', '')
    time_zone = pangle_config.get('time_zone', 0)
    currency = pangle_config.get('currency', 'usd')
    
    if not user_id or not role_id or not secure_key:
        print("❌ Missing credentials in config.yaml")
        print("   Required: user_id, role_id, secure_key")
        return False
    
    print(f"\n📋 Configuration:")
    print(f"   User ID: {user_id}")
    print(f"   Role ID: {role_id}")
    print(f"   Secure Key: {secure_key[:10]}...")
    print(f"   Time Zone: {time_zone} ({'UTC' if time_zone == 0 else f'UTC+{time_zone}'})")
    print(f"   Currency: {currency.upper()}")
    
    # Initialize fetcher
    print(f"\n🔧 Initializing Pangle fetcher...")
    try:
        fetcher = PangleFetcher(
            user_id=user_id,
            role_id=role_id,
            secure_key=secure_key,
            time_zone=time_zone,
            currency=currency,
        )
        print("   ✅ Fetcher initialized")
    except Exception as e:
        print(f"   ❌ Initialization failed: {e}")
        return False
    
    # Test date range (yesterday - for data availability)
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
    
    # Platform breakdown
    print(f"\n📱 Platform Breakdown:")
    for platform in ['android', 'ios']:
        platform_data = data.get('platform_data', {}).get(platform, {})
        rev = platform_data.get('revenue', 0)
        imps = platform_data.get('impressions', 0)
        ecpm = platform_data.get('ecpm', 0)
        
        if rev > 0 or imps > 0:
            print(f"\n   {platform.upper()}:")
            print(f"      Revenue: ${rev:.2f}")
            print(f"      Impressions: {imps:,}")
            print(f"      eCPM: ${ecpm:.2f}")
            
            # Ad type breakdown
            ad_data = platform_data.get('ad_data', {})
            for ad_type in ['banner', 'interstitial', 'rewarded']:
                ad_info = ad_data.get(ad_type, {})
                ad_rev = ad_info.get('revenue', 0)
                ad_imps = ad_info.get('impressions', 0)
                ad_ecpm = ad_info.get('ecpm', 0)
                
                if ad_rev > 0 or ad_imps > 0:
                    print(f"      - {ad_type.title()}: ${ad_rev:.2f} | {ad_imps:,} imps | ${ad_ecpm:.2f} eCPM")
    
    print("\n" + "=" * 60)
    print("✅ Pangle API test completed successfully!")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    success = test_pangle()
    sys.exit(0 if success else 1)
