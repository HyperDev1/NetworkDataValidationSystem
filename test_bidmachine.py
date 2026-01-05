"""
Test script for BidMachine SSP Reporting API fetcher.
API Docs: https://docs.bidmachine.io/docs/reporting-api
"""
import sys
import io
import requests
from datetime import datetime, timedelta, timezone
from src.config import Config
from src.fetchers import BidMachineFetcher

# Fix console encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def check_credentials(username: str, password: str) -> bool:
    """
    Check if credentials are properly configured.
    
    Args:
        username: BidMachine username
        password: BidMachine password
        
    Returns:
        True if valid, False otherwise
    """
    print("\n🔍 Checking credentials...")
    
    is_valid = True
    
    if not username or username.startswith("YOUR_"):
        print("   ❌ Username is a placeholder - please update config.yaml")
        is_valid = False
    else:
        print(f"   ✅ Username: {username}")
    
    if not password or password.startswith("YOUR_"):
        print("   ❌ Password is a placeholder - please update config.yaml")
        is_valid = False
    else:
        print(f"   ✅ Password: {'*' * len(password)}")
    
    return is_valid


def test_basic_auth():
    """Test Basic Auth connection to BidMachine."""
    print("\n" + "=" * 60)
    print("BASIC AUTH TEST")
    print("=" * 60)
    
    config = Config()
    bidmachine_config = config.get_bidmachine_config()
    
    username = bidmachine_config.get('username')
    password = bidmachine_config.get('password')
    
    if not check_credentials(username, password):
        return False
    
    print(f"\n📤 Testing Basic Auth connection...")
    
    # Test with a simple request (1 day range)
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    
    params = {
        'start': yesterday.strftime('%Y-%m-%d'),
        'end': yesterday.strftime('%Y-%m-%d'),
        'format': 'json',
        'fields': 'date,impressions,revenue'
    }
    
    try:
        response = requests.get(
            "https://api-eu.bidmachine.io/api/v1/report/ssp",
            params=params,
            auth=(username, password),
            timeout=60
        )
        
        print(f"   📥 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"   ✅ Authentication successful!")
            print(f"   📄 Response preview: {response.text[:200]}...")
            return True
        elif response.status_code == 401:
            print(f"   ❌ Authentication failed - invalid credentials")
            return False
        else:
            print(f"   ⚠️ Unexpected status: {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False


def test_fetch_data():
    """Test fetching data using BidMachineFetcher."""
    print("\n" + "=" * 60)
    print("DATA FETCH TEST")
    print("=" * 60)
    
    config = Config()
    bidmachine_config = config.get_bidmachine_config()
    
    if not bidmachine_config.get('enabled'):
        print("   ⚠️ BidMachine is not enabled in config.yaml")
        return
    
    username = bidmachine_config.get('username')
    password = bidmachine_config.get('password')
    app_bundle_ids = bidmachine_config.get('app_bundle_ids')
    
    if not check_credentials(username, password):
        return
    
    print(f"\n📊 Creating BidMachineFetcher...")
    print(f"   App Bundle IDs filter: {app_bundle_ids or '(all apps)'}")
    
    fetcher = BidMachineFetcher(
        username=username,
        password=password,
        app_bundle_ids=app_bundle_ids,
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
            if p_data.get('impressions', 0) > 0:
                print(f"\n   {platform.upper()}:")
                print(f"      Revenue: ${p_data.get('revenue', 0):.2f}")
                print(f"      Impressions: {p_data.get('impressions', 0):,}")
                print(f"      eCPM: ${p_data.get('ecpm', 0):.2f}")
                print(f"      Clicks: {p_data.get('clicks', 0):,}")
                
                # Ad type breakdown
                ad_data = p_data.get('ad_data', {})
                for ad_type in ['banner', 'interstitial', 'rewarded']:
                    ad = ad_data.get(ad_type, {})
                    if ad.get('impressions', 0) > 0:
                        print(f"         {ad_type}: ${ad.get('revenue', 0):.2f} / {ad.get('impressions', 0):,} imp / ${ad.get('ecpm', 0):.2f} eCPM")
        
        return data
        
    except Exception as e:
        print(f"   ❌ Error fetching data: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_date_range():
    """Test fetching data for a date range."""
    print("\n" + "=" * 60)
    print("DATE RANGE TEST (Last 2 days)")
    print("=" * 60)
    
    config = Config()
    bidmachine_config = config.get_bidmachine_config()
    
    if not bidmachine_config.get('enabled'):
        print("   ⚠️ BidMachine is not enabled in config.yaml")
        return
    
    username = bidmachine_config.get('username')
    password = bidmachine_config.get('password')
    
    if not check_credentials(username, password):
        return
    
    fetcher = BidMachineFetcher(
        username=username,
        password=password,
        app_bundle_ids=bidmachine_config.get('app_bundle_ids'),
    )
    
    # Fetch last 2 days (yesterday and day before)
    end_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=1)
    
    print(f"\n📅 Fetching data for: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    try:
        data = fetcher.fetch_data(start_date, end_date)
        
        print(f"\n✅ Data fetched successfully!")
        print(f"   Total Revenue (2 days): ${data.get('revenue', 0):.2f}")
        print(f"   Total Impressions (2 days): {data.get('impressions', 0):,}")
        print(f"   Average eCPM: ${data.get('ecpm', 0):.2f}")
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("BidMachine SSP API Test Suite")
    print("API Docs: https://docs.bidmachine.io/docs/reporting-api")
    print("=" * 60)
    
    # Test 1: Basic Auth
    auth_ok = test_basic_auth()
    
    if not auth_ok:
        print("\n❌ Authentication failed. Please check your credentials in config.yaml")
        return
    
    # Test 2: Fetch Data
    test_fetch_data()
    
    # Test 3: Date Range
    test_date_range()
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
