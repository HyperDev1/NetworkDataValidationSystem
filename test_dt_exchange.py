"""
Test script for DT Exchange (Digital Turbine) Reporting API fetcher.
API Docs: https://developer.digitalturbine.com/hc/en-us/articles/8101286018717-DT-Exchange-Reporting-API
"""
import sys
import io
import requests
from datetime import datetime, timedelta, timezone
from src.config import Config
from src.fetchers import DTExchangeFetcher

# Fix console encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def check_credentials(client_id: str, client_secret: str) -> bool:
    """
    Check if credentials are properly configured.
    
    Args:
        client_id: DT Exchange OAuth Client ID
        client_secret: DT Exchange OAuth Client Secret
        
    Returns:
        True if valid, False otherwise
    """
    print("\n🔍 Checking credentials...")
    
    is_valid = True
    
    if not client_id or client_id.startswith("YOUR_"):
        print("   ❌ Client ID is a placeholder - please update config.yaml")
        is_valid = False
    else:
        print(f"   ✅ Client ID: {client_id[:8]}...{client_id[-4:] if len(client_id) > 12 else client_id}")
    
    if not client_secret or client_secret.startswith("YOUR_"):
        print("   ❌ Client Secret is a placeholder - please update config.yaml")
        is_valid = False
    else:
        print(f"   ✅ Client Secret: {client_secret[:4]}...{client_secret[-4:] if len(client_secret) > 8 else '****'}")
    
    return is_valid


def test_basic_auth():
    """Test OAuth 2.0 authentication to DT Exchange API."""
    print("\n" + "=" * 60)
    print("OAUTH 2.0 AUTH TEST")
    print("=" * 60)
    
    config = Config()
    dt_config = config.get_dt_exchange_config()
    
    client_id = dt_config.get('client_id')
    client_secret = dt_config.get('client_secret')
    
    if not check_credentials(client_id, client_secret):
        return False
    
    print(f"\n📤 Testing OAuth 2.0 authentication...")
    
    # Create fetcher and test auth
    fetcher = DTExchangeFetcher(
        client_id=client_id,
        client_secret=client_secret,
        source=dt_config.get('source', 'mediation'),
    )
    
    result = fetcher.debug_auth()
    
    if result['success']:
        print(f"   ✅ Authentication successful!")
        print(f"   🔑 Token preview: {result['token_preview']}")
        return True
    else:
        print(f"   ❌ Authentication failed: {result['error']}")
        return False


def test_report_request():
    """Test report request to DT Exchange API."""
    print("\n" + "=" * 60)
    print("REPORT REQUEST TEST")
    print("=" * 60)
    
    config = Config()
    dt_config = config.get_dt_exchange_config()
    
    client_id = dt_config.get('client_id')
    client_secret = dt_config.get('client_secret')
    
    if not check_credentials(client_id, client_secret):
        return False
    
    # Use yesterday's date (12-hour data delay)
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    date_str = yesterday.strftime('%Y-%m-%d')
    
    print(f"\n📤 Requesting report for date: {date_str}")
    
    fetcher = DTExchangeFetcher(
        client_id=client_id,
        client_secret=client_secret,
        source=dt_config.get('source', 'mediation'),
        app_ids=dt_config.get('app_ids'),
    )
    
    result = fetcher.debug_report_request(date_str, date_str)
    
    if result['success']:
        print(f"   ✅ Report request successful!")
        print(f"   📄 Report URL: {result['report_url'][:80]}...")
        return True
    else:
        print(f"   ❌ Report request failed: {result['error']}")
        return False


def test_fetch_data():
    """Test full data fetch from DT Exchange API."""
    print("\n" + "=" * 60)
    print("FULL DATA FETCH TEST")
    print("=" * 60)
    
    config = Config()
    dt_config = config.get_dt_exchange_config()
    
    client_id = dt_config.get('client_id')
    client_secret = dt_config.get('client_secret')
    
    if not check_credentials(client_id, client_secret):
        return None
    
    # Use yesterday (12-hour data delay)
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    
    print(f"\n📤 Fetching data for: {yesterday.strftime('%Y-%m-%d')}")
    print("   ⏳ This may take a few minutes (async report generation)...")
    
    try:
        fetcher = DTExchangeFetcher(
            client_id=client_id,
            client_secret=client_secret,
            source=dt_config.get('source', 'mediation'),
            app_ids=dt_config.get('app_ids'),
        )
        
        data = fetcher.fetch_data(yesterday, yesterday)
        
        print(f"\n   ✅ Data fetch successful!")
        return data
        
    except Exception as e:
        print(f"\n   ❌ Data fetch failed: {str(e)}")
        return None


def display_results(data: dict):
    """Display fetched data in a formatted way."""
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    
    if not data:
        print("   No data to display")
        return
    
    print(f"\n📊 Network: {data.get('network', 'Unknown')}")
    print(f"📅 Date Range: {data['date_range']['start']} to {data['date_range']['end']}")
    
    print(f"\n💰 Total Revenue: ${data.get('revenue', 0):,.2f}")
    print(f"👁️  Total Impressions: {data.get('impressions', 0):,}")
    print(f"📈 Total eCPM: ${data.get('ecpm', 0):,.4f}")
    print(f"🖱️  Total Clicks: {data.get('clicks', 0):,}")
    
    # Platform breakdown
    platform_data = data.get('platform_data', {})
    
    for platform in ['android', 'ios']:
        p_data = platform_data.get(platform, {})
        if p_data.get('impressions', 0) > 0:
            print(f"\n📱 {platform.upper()}:")
            print(f"   💰 Revenue: ${p_data.get('revenue', 0):,.2f}")
            print(f"   👁️  Impressions: {p_data.get('impressions', 0):,}")
            print(f"   📈 eCPM: ${p_data.get('ecpm', 0):,.4f}")
            print(f"   🖱️  Clicks: {p_data.get('clicks', 0):,}")
            
            # Ad type breakdown
            ad_data = p_data.get('ad_data', {})
            for ad_type in ['banner', 'interstitial', 'rewarded']:
                a_data = ad_data.get(ad_type, {})
                if a_data.get('impressions', 0) > 0:
                    print(f"      📋 {ad_type.capitalize()}:")
                    print(f"         Revenue: ${a_data.get('revenue', 0):,.2f}")
                    print(f"         Impressions: {a_data.get('impressions', 0):,}")
                    print(f"         eCPM: ${a_data.get('ecpm', 0):,.4f}")


def test_multi_day():
    """Test fetching data for multiple days."""
    print("\n" + "=" * 60)
    print("MULTI-DAY FETCH TEST (Last 7 days)")
    print("=" * 60)
    
    config = Config()
    dt_config = config.get_dt_exchange_config()
    
    client_id = dt_config.get('client_id')
    client_secret = dt_config.get('client_secret')
    
    if not check_credentials(client_id, client_secret):
        return None
    
    # Last 7 days (excluding today due to 12-hour delay)
    end_date = datetime.now(timezone.utc) - timedelta(days=1)
    start_date = end_date - timedelta(days=6)
    
    print(f"\n📤 Fetching data from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print("   ⏳ This may take a few minutes...")
    
    try:
        fetcher = DTExchangeFetcher(
            client_id=client_id,
            client_secret=client_secret,
            source=dt_config.get('source', 'mediation'),
            app_ids=dt_config.get('app_ids'),
        )
        
        data = fetcher.fetch_data(start_date, end_date)
        
        print(f"\n   ✅ Multi-day fetch successful!")
        return data
        
    except Exception as e:
        print(f"\n   ❌ Multi-day fetch failed: {str(e)}")
        return None


def main():
    """Run all DT Exchange API tests."""
    print("\n" + "=" * 60)
    print("DT EXCHANGE (DIGITAL TURBINE) API TEST SUITE")
    print("=" * 60)
    
    # Load config
    try:
        config = Config()
        dt_config = config.get_dt_exchange_config()
    except FileNotFoundError as e:
        print(f"\n❌ {e}")
        return
    
    # Check if enabled
    if not dt_config.get('enabled', False):
        print("\n⚠️  DT Exchange is disabled in config.yaml")
        print("   Set 'enabled: true' under dt_exchange section to run tests")
        return
    
    print(f"\n📋 Configuration loaded:")
    print(f"   Source: {dt_config.get('source', 'mediation')}")
    print(f"   App IDs filter: {dt_config.get('app_ids') or '(all apps)'}")
    
    # Run tests
    results = {}
    
    # Test 1: Authentication
    results['auth'] = test_basic_auth()
    
    if not results['auth']:
        print("\n❌ Authentication failed - skipping remaining tests")
        return
    
    # Test 2: Report Request
    results['report_request'] = test_report_request()
    
    if not results['report_request']:
        print("\n❌ Report request failed - skipping full fetch test")
        return
    
    # Test 3: Full Data Fetch
    data = test_fetch_data()
    results['fetch'] = data is not None
    
    if data:
        display_results(data)
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"   🔐 Auth Test: {'✅ Passed' if results['auth'] else '❌ Failed'}")
    print(f"   📄 Report Request Test: {'✅ Passed' if results['report_request'] else '❌ Failed'}")
    print(f"   📊 Data Fetch Test: {'✅ Passed' if results['fetch'] else '❌ Failed'}")
    
    if all(results.values()):
        print("\n🎉 All tests passed! DT Exchange integration is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Please check the output above for details.")


if __name__ == "__main__":
    main()
