"""
Test script for Meta Audience Network fetcher.
Tests the T-3 daily data fetching approach for stable revenue data.
"""
import requests
from datetime import datetime, timedelta, timezone
from src.config import Config
from src.fetchers import MetaFetcher


def check_token_info(access_token: str):
    """Check token info and permissions."""
    print("\n🔍 Checking token info...")
    
    url = "https://graph.facebook.com/v18.0/me"
    params = {"access_token": access_token, "fields": "id,name"}
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        print(f"   Token User/App ID: {data.get('id')}")
        print(f"   Token Name: {data.get('name')}")
    else:
        print(f"   ❌ Token check failed: {response.text[:200]}")


def test_meta_fetcher():
    """Test Meta Audience Network fetcher with T-3 daily mode."""
    print("=" * 60)
    print("META AUDIENCE NETWORK FETCHER TEST (T-3 Daily Mode)")
    print("=" * 60)
    
    # Load config
    config = Config()
    meta_config = config.get_meta_config()
    
    print(f"\n📋 Configuration:")
    print(f"   Enabled: {meta_config.get('enabled')}")
    print(f"   Business ID: {meta_config.get('business_id')}")
    print(f"   Access Token: {meta_config.get('access_token', '')[:20]}...")
    
    if not meta_config.get('enabled'):
        print("\n❌ Meta is not enabled in config.yaml")
        return
    
    access_token = meta_config.get('access_token')
    business_id = meta_config.get('business_id')
    
    if not access_token:
        print("\n❌ Access token is missing")
        return
    
    if not business_id:
        print("\n❌ Business ID is missing")
        return
    
    # Debug: Check token info
    check_token_info(access_token)
    
    # Initialize fetcher
    print(f"\n" + "=" * 60)
    print("FETCHER TEST")
    print("=" * 60)
    print(f"\n🔧 Initializing MetaFetcher...")
    fetcher = MetaFetcher(
        access_token=access_token,
        business_id=business_id
    )
    print(f"   ✅ Network name: {fetcher.get_network_name()}")
    print(f"   ✅ Data delay: {fetcher.DATA_DELAY_DAYS} days (T-3)")
    
    # Meta T-3 daily mode - request data from 3 days ago
    # Daily data requires ~3 days to stabilize per Meta API docs
    now_utc = datetime.now(timezone.utc)
    target_date = now_utc.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=3)
    
    print(f"\n📅 Requesting Meta daily data for: {target_date.strftime('%Y-%m-%d')}")
    print(f"   (T-3: 3 days ago - using daily aggregation for stable data)")
    
    # Fetch daily data
    print(f"\n📥 Fetching daily data...")
    try:
        data = fetcher.fetch_data(target_date, target_date)
        
        print(f"\n✅ SUCCESS!")
        print(f"\n📊 Results:")
        print(f"   Total Revenue: ${data['revenue']:.2f}")
        print(f"   Total Impressions: {data['impressions']:,}")
        print(f"   Total eCPM: ${data['ecpm']:.2f}")
        print(f"   Date Range: {data.get('date_range', {})}")
        
        print(f"\n📱 Platform Breakdown:")
        for platform, pdata in data['platform_data'].items():
            if pdata['impressions'] > 0:
                print(f"\n   {platform.upper()}:")
                print(f"      Revenue: ${pdata['revenue']:.2f}")
                print(f"      Impressions: {pdata['impressions']:,}")
                print(f"      eCPM: ${pdata['ecpm']:.2f}")
                
                print(f"      Ad Types:")
                for ad_type, ad_data in pdata['ad_data'].items():
                    if ad_data['impressions'] > 0:
                        print(f"         {ad_type}: ${ad_data['revenue']:.2f} | {ad_data['impressions']:,} imps | ${ad_data['ecpm']:.2f} eCPM")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()


def test_date_calculation():
    """Test that T-3 date calculation is correct."""
    print("\n" + "=" * 60)
    print("DATE CALCULATION TEST")
    print("=" * 60)
    
    now_utc = datetime.now(timezone.utc)
    today = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Standard networks use T-1
    t1_date = today - timedelta(days=1)
    
    # Meta uses T-3
    t3_date = today - timedelta(days=3)
    
    print(f"\n📅 Today (UTC): {today.strftime('%Y-%m-%d')}")
    print(f"📅 T-1 (other networks): {t1_date.strftime('%Y-%m-%d')}")
    print(f"📅 T-3 (Meta): {t3_date.strftime('%Y-%m-%d')}")
    
    # Verify delay constant
    from src.fetchers import MetaFetcher
    assert MetaFetcher.DATA_DELAY_DAYS == 3, f"Expected DATA_DELAY_DAYS=3, got {MetaFetcher.DATA_DELAY_DAYS}"
    print(f"\n✅ MetaFetcher.DATA_DELAY_DAYS = {MetaFetcher.DATA_DELAY_DAYS} (correct)")


if __name__ == "__main__":
    test_date_calculation()
    test_meta_fetcher()

