"""
Test script for Chartboost Mediation Reporting API fetcher.
API Docs: https://docs.chartboost.com/en/mediation/reference/mediation-reporting-api/
"""
import sys
import io
import requests
from datetime import datetime, timedelta, timezone
from src.config import Config
from src.fetchers.chartboost_fetcher import ChartboostFetcher

# Fix console encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def check_credentials(client_id: str, client_secret: str) -> bool:
    """
    Check if credentials are properly configured.
    
    Args:
        client_id: Chartboost OAuth Client ID
        client_secret: Chartboost OAuth Client Secret
        
    Returns:
        True if valid, False otherwise
    """
    print("\n🔍 Checking credentials...")
    
    is_valid = True
    
    if not client_id or client_id.startswith("YOUR_"):
        print("   ❌ Client ID is a placeholder - please update config.yaml")
        is_valid = False
    else:
        print(f"   ✅ Client ID: {client_id[:8]}...{client_id[-4:]}")
    
    if not client_secret or client_secret.startswith("YOUR_"):
        print("   ❌ Client Secret is a placeholder - please update config.yaml")
        is_valid = False
    else:
        print(f"   ✅ Client Secret: {client_secret[:8]}...{client_secret[-4:]}")
    
    return is_valid


def test_basic_auth():
    """Test OAuth authentication to Chartboost API."""
    print("\n" + "=" * 60)
    print("OAUTH AUTHENTICATION TEST")
    print("=" * 60)
    
    config = Config()
    chartboost_config = config.get_chartboost_config()
    
    client_id = chartboost_config.get('client_id')
    client_secret = chartboost_config.get('client_secret')
    
    if not check_credentials(client_id, client_secret):
        return False
    
    print(f"\n📤 Testing OAuth authentication...")
    
    payload = {
        'client_id': client_id,
        'client_secret': client_secret,
        'audience': 'https://public.api.gateway.chartboost.com',
        'grant_type': 'client_credentials',
    }
    
    headers = {
        'Content-Type': 'application/json',
    }
    
    try:
        response = requests.post(
            "https://api.chartboost.com/v5/oauth/token",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        print(f"   📥 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            access_token = data.get('access_token', '')
            expires_in = data.get('expires_in', 0)
            print(f"   ✅ Authentication successful!")
            print(f"   Token: {access_token[:20]}...{access_token[-10:]}")
            print(f"   Expires in: {expires_in} seconds ({expires_in // 3600} hours)")
            return True
        else:
            print(f"   ❌ Authentication failed")
            try:
                error_data = response.json()
                print(f"   Error: {error_data}")
            except:
                print(f"   Response: {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False


def test_report_request():
    """Test report API request."""
    print("\n" + "=" * 60)
    print("REPORT API TEST")
    print("=" * 60)
    
    config = Config()
    chartboost_config = config.get_chartboost_config()
    
    client_id = chartboost_config.get('client_id')
    client_secret = chartboost_config.get('client_secret')
    app_ids = chartboost_config.get('app_ids', '')
    time_zone = chartboost_config.get('time_zone', 'UTC')
    app_platform_map = chartboost_config.get('app_platform_map', {})
    
    if not check_credentials(client_id, client_secret):
        return False
    
    # Initialize fetcher
    fetcher = ChartboostFetcher(
        client_id=client_id,
        client_secret=client_secret,
        app_ids=app_ids,
        time_zone=time_zone,
        app_platform_map=app_platform_map,
    )
    
    # Test date range (yesterday to today)
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=2)
    
    # Run debug test
    fetcher._test_report_request(start_date, end_date)
    
    return True


def test_fetch_data():
    """Test full data fetch."""
    print("\n" + "=" * 60)
    print("FULL DATA FETCH TEST")
    print("=" * 60)
    
    config = Config()
    chartboost_config = config.get_chartboost_config()
    
    if not chartboost_config.get('enabled'):
        print("\n⚠️ Chartboost is disabled in config.yaml")
        print("   Set 'enabled: true' to run this test")
        return False
    
    client_id = chartboost_config.get('client_id')
    client_secret = chartboost_config.get('client_secret')
    app_ids = chartboost_config.get('app_ids', '')
    time_zone = chartboost_config.get('time_zone', 'UTC')
    app_platform_map = chartboost_config.get('app_platform_map', {})
    
    if not check_credentials(client_id, client_secret):
        return False
    
    # Initialize fetcher
    fetcher = ChartboostFetcher(
        client_id=client_id,
        client_secret=client_secret,
        app_ids=app_ids,
        time_zone=time_zone,
        app_platform_map=app_platform_map,
    )
    
    # Test date range (yesterday)
    end_date = datetime.now(timezone.utc) - timedelta(days=1)
    start_date = end_date
    
    print(f"\n📅 Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    try:
        data = fetcher.fetch_data(start_date, end_date)
        
        print("\n" + "=" * 60)
        print("RESULTS SUMMARY")
        print("=" * 60)
        
        print(f"\n📊 Overall Metrics:")
        print(f"   Network: {data.get('network')}")
        print(f"   Date Range: {data.get('date_range')}")
        print(f"   Total Revenue: ${data.get('revenue', 0):.2f}")
        print(f"   Total Impressions: {data.get('impressions', 0):,}")
        print(f"   Total Requests: {data.get('requests', 0):,}")
        print(f"   Overall eCPM: ${data.get('ecpm', 0):.2f}")
        
        platform_data = data.get('platform_data', {})
        
        for platform, p_data in platform_data.items():
            print(f"\n📱 Platform: {platform.upper()}")
            print(f"   Revenue: ${p_data.get('revenue', 0):.2f}")
            print(f"   Impressions: {p_data.get('impressions', 0):,}")
            print(f"   Requests: {p_data.get('requests', 0):,}")
            print(f"   eCPM: ${p_data.get('ecpm', 0):.2f}")
            
            ad_data = p_data.get('ad_data', {})
            for ad_type, ad_metrics in ad_data.items():
                if ad_metrics.get('impressions', 0) > 0 or ad_metrics.get('revenue', 0) > 0:
                    print(f"\n   📋 {ad_type.upper()}:")
                    print(f"      Revenue: ${ad_metrics.get('revenue', 0):.2f}")
                    print(f"      Impressions: {ad_metrics.get('impressions', 0):,}")
                    print(f"      eCPM: ${ad_metrics.get('ecpm', 0):.2f}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error fetching data: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("CHARTBOOST FETCHER TEST SUITE")
    print("=" * 60)
    print("API Docs: https://docs.chartboost.com/en/mediation/reference/mediation-reporting-api/")
    
    config = Config()
    chartboost_config = config.get_chartboost_config()
    
    if not chartboost_config:
        print("\n❌ Chartboost configuration not found in config.yaml")
        print("   Please add chartboost configuration section")
        return
    
    print(f"\n📋 Configuration:")
    print(f"   Enabled: {chartboost_config.get('enabled', False)}")
    print(f"   Time Zone: {chartboost_config.get('time_zone', 'UTC')}")
    if chartboost_config.get('app_ids'):
        print(f"   App IDs: {chartboost_config.get('app_ids')}")
    if chartboost_config.get('app_platform_map'):
        print(f"   App Platform Map: {chartboost_config.get('app_platform_map')}")
    
    # Run tests
    auth_ok = test_basic_auth()
    
    if auth_ok:
        test_report_request()
        test_fetch_data()
    else:
        print("\n⚠️ Skipping further tests due to authentication failure")
    
    print("\n" + "=" * 60)
    print("TEST SUITE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
