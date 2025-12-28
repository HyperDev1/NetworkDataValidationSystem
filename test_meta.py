"""
Test script for Meta Audience Network fetcher.
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
    """Test Meta Audience Network fetcher."""
    print("=" * 60)
    print("META AUDIENCE NETWORK FETCHER TEST")
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
    
    # Meta has 3-day reporting delay - request data from 3 days ago (UTC)
    now_utc = datetime.now(timezone.utc)
    meta_delay_days = 3
    end_date = now_utc.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1) - timedelta(days=meta_delay_days)
    start_date = end_date
    
    print(f"\n📅 Requesting Meta data for: {start_date.strftime('%Y-%m-%d')} (UTC)")
    print(f"   (This is {meta_delay_days + 1} days ago - Meta's latest available data)")
    
    # Fetch data
    print(f"\n📥 Fetching data...")
    try:
        data = fetcher.fetch_data(start_date, end_date)
        
        print(f"\n✅ SUCCESS!")
        print(f"\n📊 Results:")
        print(f"   Total Revenue: ${data['revenue']:.2f}")
        print(f"   Total Impressions: {data['impressions']:,}")
        print(f"   Total eCPM: ${data['ecpm']:.2f}")
        
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


if __name__ == "__main__":
    test_meta_fetcher()

