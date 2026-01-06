"""
Test script for Liftoff (Vungle) Publisher Reporting API 2.0 fetcher.
API Docs: https://support.vungle.com/hc/en-us/articles/211365828-Publisher-Reporting-API-2-0
"""
import sys
import io
import requests
from datetime import datetime, timedelta, timezone
from src.config import Config
from src.fetchers import LiftoffFetcher

# Fix console encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def check_credentials(api_key: str) -> bool:
    """
    Check if credentials are properly configured.
    
    Args:
        api_key: Liftoff API Key
        
    Returns:
        True if valid, False otherwise
    """
    print("\n🔍 Checking credentials...")
    
    is_valid = True
    
    if not api_key or api_key.startswith("YOUR_"):
        print("   ❌ API Key is a placeholder - please update config.yaml")
        is_valid = False
    else:
        print(f"   ✅ API Key: {api_key[:8]}...{api_key[-4:]}")
    
    return is_valid


def test_basic_auth():
    """Test Bearer Token authentication to Liftoff API."""
    print("\n" + "=" * 60)
    print("BEARER TOKEN AUTH TEST")
    print("=" * 60)
    
    config = Config()
    liftoff_config = config.get_liftoff_config()
    
    api_key = liftoff_config.get('api_key')
    
    if not check_credentials(api_key):
        return False
    
    print(f"\n📤 Testing Bearer Token authentication...")
    
    # Test with a simple request (1 day range)
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Vungle-Version': '1',
        'Accept': 'application/json',
    }
    
    params = {
        'start': yesterday.strftime('%Y-%m-%d'),
        'end': yesterday.strftime('%Y-%m-%d'),
        'dimensions': 'date',
        'aggregates': 'impressions,revenue',
    }
    
    try:
        response = requests.get(
            "https://report.api.vungle.com/ext/pub/reports/performance",
            headers=headers,
            params=params,
            timeout=60
        )
        
        print(f"   📥 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"   ✅ Authentication successful!")
            preview = response.text[:200] if response.text else "(empty response)"
            print(f"   📄 Response preview: {preview}...")
            return True
        elif response.status_code == 401:
            print(f"   ❌ Authentication failed - invalid API key")
            print(f"   💡 Get your API key from Liftoff Dashboard → Reports page")
            return False
        else:
            print(f"   ⚠️ Unexpected status: {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False


def test_fetch_data():
    """Test fetching data using LiftoffFetcher."""
    print("\n" + "=" * 60)
    print("DATA FETCH TEST")
    print("=" * 60)
    
    config = Config()
    liftoff_config = config.get_liftoff_config()
    
    if not liftoff_config.get('enabled'):
        print("   ⚠️ Liftoff is not enabled in config.yaml")
        return
    
    api_key = liftoff_config.get('api_key')
    application_ids = liftoff_config.get('application_ids')
    
    if not check_credentials(api_key):
        return
    
    print(f"\n📊 Creating LiftoffFetcher...")
    print(f"   Application IDs filter: {application_ids or '(all apps)'}")
    
    fetcher = LiftoffFetcher(
        api_key=api_key,
        application_ids=application_ids,
    )
    
    # Fetch yesterday's data
    end_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    start_date = end_date
    
    print(f"\n📅 Fetching data for: {start_date.strftime('%Y-%m-%d')}")
    
    try:
        data = fetcher.fetch_data(start_date, end_date)
        
        print(f"\n✅ Data fetched successfully!")
        print(f"\n{'=' * 40}")
        print(f"📈 SUMMARY")
        print(f"{'=' * 40}")
        print(f"   Network: {data.get('network')}")
        print(f"   Date Range: {data.get('date_range', {}).get('start')} to {data.get('date_range', {}).get('end')}")
        print(f"   Total Revenue: ${data.get('revenue', 0):.2f}")
        print(f"   Total Impressions: {data.get('impressions', 0):,}")
        print(f"   Total eCPM: ${data.get('ecpm', 0):.2f}")
        print(f"   Total Clicks: {data.get('clicks', 0):,}")
        
        # Platform breakdown
        print(f"\n{'=' * 40}")
        print(f"📱 PLATFORM BREAKDOWN")
        print(f"{'=' * 40}")
        
        for platform in ['android', 'ios']:
            p_data = data.get('platform_data', {}).get(platform, {})
            if p_data.get('impressions', 0) > 0 or p_data.get('revenue', 0) > 0:
                print(f"\n   {platform.upper()}:")
                print(f"      Revenue: ${p_data.get('revenue', 0):.2f}")
                print(f"      Impressions: {p_data.get('impressions', 0):,}")
                print(f"      eCPM: ${p_data.get('ecpm', 0):.2f}")
                print(f"      Clicks: {p_data.get('clicks', 0):,}")
                
                # Ad type breakdown
                ad_data = p_data.get('ad_data', {})
                for ad_type in ['banner', 'interstitial', 'rewarded']:
                    ad = ad_data.get(ad_type, {})
                    if ad.get('impressions', 0) > 0 or ad.get('revenue', 0) > 0:
                        print(f"         {ad_type}: ${ad.get('revenue', 0):.2f} / {ad.get('impressions', 0):,} imp / ${ad.get('ecpm', 0):.2f} eCPM")
        
        # Note about banner
        print(f"\n💡 Note: Liftoff serves video ads (interstitial/rewarded) and banner ads.")
        
        return data
        
    except Exception as e:
        print(f"   ❌ Error fetching data: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_date_range():
    """Test fetching data for a date range."""
    print("\n" + "=" * 60)
    print("DATE RANGE TEST (Last 3 days)")
    print("=" * 60)
    
    config = Config()
    liftoff_config = config.get_liftoff_config()
    
    if not liftoff_config.get('enabled'):
        print("   ⚠️ Liftoff is not enabled in config.yaml")
        return
    
    api_key = liftoff_config.get('api_key')
    
    if not check_credentials(api_key):
        return
    
    fetcher = LiftoffFetcher(
        api_key=api_key,
        application_ids=liftoff_config.get('application_ids'),
    )
    
    # Fetch last 3 days
    end_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    start_date = end_date - timedelta(days=2)
    
    print(f"\n📅 Fetching data for: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    try:
        data = fetcher.fetch_data(start_date, end_date)
        
        print(f"\n✅ Date range test successful!")
        print(f"   Total Revenue: ${data.get('revenue', 0):.2f}")
        print(f"   Total Impressions: {data.get('impressions', 0):,}")
        print(f"   Total eCPM: ${data.get('ecpm', 0):.2f}")
        
        return data
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return None


def main():
    """Run all Liftoff API tests."""
    print("=" * 60)
    print("LIFTOFF (VUNGLE) API TEST SUITE")
    print("=" * 60)
    print("\nAPI Docs: https://support.vungle.com/hc/en-us/articles/211365828-Publisher-Reporting-API-2-0")
    
    # Test 1: Basic Auth
    auth_ok = test_basic_auth()
    
    if not auth_ok:
        print("\n" + "=" * 60)
        print("❌ Authentication failed. Please check your config.yaml")
        print("=" * 60)
        print("\nTo configure Liftoff:")
        print("1. Go to Liftoff Dashboard → Reports page")
        print("2. Copy your API Key")
        print("3. Add to config.yaml under networks.liftoff.api_key")
        return
    
    # Test 2: Fetch data
    test_fetch_data()
    
    # Test 3: Date range
    test_date_range()
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()
