"""
Test script for Moloco Publisher Summary API fetcher.
API Docs: https://help.publisher.moloco.com/hc/en-us/articles/26777697929111-Get-performance-data-using-the-Publisher-Summary-API
"""
import sys
import io
import requests
from datetime import datetime, timedelta, timezone
from src.config import Config
from src.fetchers import MolocoFetcher

# Fix console encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def check_credentials(email: str, password: str, publisher_id: str) -> bool:
    """
    Check if credentials are properly configured.
    
    Args:
        email: Moloco email
        password: Moloco password
        publisher_id: Moloco publisher ID
        
    Returns:
        True if valid, False otherwise
    """
    print("\n🔍 Checking credentials...")
    
    is_valid = True
    
    if not email or email.startswith("YOUR_"):
        print("   ❌ Email is a placeholder - please update config.yaml")
        is_valid = False
    else:
        print(f"   ✅ Email: {email}")
    
    if not password or password.startswith("YOUR_"):
        print("   ❌ Password is a placeholder - please update config.yaml")
        is_valid = False
    else:
        print(f"   ✅ Password: {'*' * len(password)}")
    
    if not publisher_id or publisher_id.startswith("YOUR_"):
        print("   ❌ Publisher ID is a placeholder - please update config.yaml")
        is_valid = False
    else:
        print(f"   ✅ Publisher ID: {publisher_id}")
    
    return is_valid


def test_auth_token():
    """Test getting auth token from Moloco."""
    print("\n" + "=" * 60)
    print("AUTH TOKEN TEST")
    print("=" * 60)
    
    config = Config()
    moloco_config = config.get_moloco_config()
    
    email = moloco_config.get('email')
    password = moloco_config.get('password')
    platform_id = moloco_config.get('platform_id')
    
    if not check_credentials(email, password, platform_id):
        return None
    
    print(f"\n📤 Requesting access token...")
    
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }
    
    payload = {
        'email': email,
        'password': password,
        'workplace_id': platform_id,
    }
    
    try:
        response = requests.post(
            "https://sdkpubapi.moloco.com/api/adcloud/publisher/v1/auth/tokens",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"\n📊 Response:")
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            token = data.get('token', '')
            token_type = data.get('token_type', '')
            
            print(f"   Token Type: {token_type}")
            print(f"   Token: {token[:30]}..." if len(token) > 30 else f"   Token: {token}")
            
            if token_type == 'UPDATE_PASSWORD':
                print("\n   ⚠️  Password update required!")
                print("   Please log in to Moloco Publisher Portal to update your password.")
                return None
            
            print("\n   ✅ Token obtained successfully!")
            return token
        else:
            try:
                error_data = response.json()
                print(f"   Error: {error_data}")
            except:
                print(f"   Error: {response.text[:500]}")
            return None
            
    except Exception as e:
        print(f"\n❌ Request failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_moloco_fetcher():
    """Test Moloco Publisher Summary API fetcher."""
    print("=" * 60)
    print("MOLOCO PUBLISHER SUMMARY API FETCHER TEST")
    print("=" * 60)
    
    # Load config
    try:
        config = Config()
        print("✅ Configuration loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load configuration: {str(e)}")
        return
    
    moloco_config = config.get_moloco_config()
    
    print(f"\n📋 Configuration:")
    print(f"   Enabled: {moloco_config.get('enabled')}")
    print(f"   Email: {moloco_config.get('email')}")
    print(f"   Password: {'*' * len(moloco_config.get('password', ''))}")
    print(f"   Platform ID: {moloco_config.get('platform_id')} (for auth)")
    print(f"   Publisher ID: {moloco_config.get('publisher_id')} (for API)")
    print(f"   App Bundle IDs: {moloco_config.get('app_bundle_ids') or 'All apps'}")
    print(f"   Timezone: {moloco_config.get('time_zone', 'UTC')}")
    
    if not moloco_config.get('enabled'):
        print("\n❌ Moloco is not enabled in config.yaml")
        print("   Set 'enabled: true' under networks.moloco to enable")
        return
    
    email = moloco_config.get('email')
    password = moloco_config.get('password')
    platform_id = moloco_config.get('platform_id')
    publisher_id = moloco_config.get('publisher_id')
    
    # Check credentials
    if not check_credentials(email, password, platform_id):
        return
    
    # Initialize fetcher
    print(f"\n" + "=" * 60)
    print("FETCHER TEST")
    print("=" * 60)
    print(f"\n🔧 Initializing MolocoFetcher...")
    
    try:
        fetcher = MolocoFetcher(
            email=email,
            password=password,
            platform_id=platform_id,
            publisher_id=publisher_id,
            app_bundle_ids=moloco_config.get('app_bundle_ids'),
            time_zone=moloco_config.get('time_zone', 'UTC'),
            ad_unit_mapping=moloco_config.get('ad_unit_mapping', {})
        )
        print(f"   ✅ Network name: {fetcher.get_network_name()}")
        if moloco_config.get('ad_unit_mapping'):
            print(f"   ✅ Ad unit mapping: {len(moloco_config.get('ad_unit_mapping'))} units configured")
    except Exception as e:
        print(f"   ❌ Failed to initialize fetcher: {str(e)}")
        return
    
    # Set date range - yesterday (as today's data may not be available)
    now_utc = datetime.now(timezone.utc)
    end_date = now_utc.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    start_date = end_date
    
    print(f"\n📅 Requesting Moloco data for: {start_date.strftime('%Y-%m-%d')} (UTC)")
    
    # Fetch data
    print(f"\n📥 Fetching data...")
    try:
        data = fetcher.fetch_data(start_date, end_date)
        
        print(f"\n✅ SUCCESS!")
        print(f"\n📊 Results:")
        print(f"   Total Revenue: ${data['revenue']:.2f}")
        print(f"   Total Impressions: {data['impressions']:,}")
        print(f"   Total eCPM: ${data['ecpm']:.2f}")
        print(f"   Total Requests: {data.get('requests', 0):,}")
        print(f"   Total Fills: {data.get('fills', 0):,}")
        print(f"   Total Clicks: {data.get('clicks', 0):,}")
        
        # Calculate fill rate
        if data.get('requests', 0) > 0:
            fill_rate = (data.get('fills', 0) / data.get('requests', 0)) * 100
            print(f"   Fill Rate: {fill_rate:.2f}%")
        
        print(f"\n📱 Platform Breakdown:")
        for platform, pdata in data['platform_data'].items():
            if pdata['impressions'] > 0:
                print(f"\n   {platform.upper()}:")
                print(f"      Revenue: ${pdata['revenue']:.2f}")
                print(f"      Impressions: {pdata['impressions']:,}")
                print(f"      eCPM: ${pdata['ecpm']:.2f}")
                print(f"      Requests: {pdata.get('requests', 0):,}")
                print(f"      Fills: {pdata.get('fills', 0):,}")
                print(f"      Clicks: {pdata.get('clicks', 0):,}")
                
                print(f"      Ad Types:")
                for ad_type, ad_data in pdata['ad_data'].items():
                    if ad_data['impressions'] > 0:
                        print(f"         {ad_type}: ${ad_data['revenue']:.2f} | {ad_data['impressions']:,} imps | ${ad_data['ecpm']:.2f} eCPM")
        
        # Show if no data
        total_platform_impressions = sum(
            pdata['impressions'] for pdata in data['platform_data'].values()
        )
        if total_platform_impressions == 0 and data['impressions'] == 0:
            print(f"\n   ⚠️  No data available for this date")
            print(f"       This could mean:")
            print(f"       - No ad traffic on {start_date.strftime('%Y-%m-%d')}")
            print(f"       - Data is not yet available (try an earlier date)")
            print(f"       - Check if your Platform ID is correct")
        
        print(f"\n" + "=" * 60)
        print("✅ Moloco test completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        error_str = str(e)
        print(f"\n❌ ERROR: {error_str}")
        
        # Provide helpful error messages
        if "401" in error_str or "unauthorized" in error_str.lower():
            print("\n" + "=" * 60)
            print("🔑 Authentication Error - Please check:")
            print("=" * 60)
            print("1. Email is correct in config.yaml")
            print("2. Password is correct in config.yaml")
            print("3. Platform ID (workplace_id) is correct")
            print("\n   To get your credentials:")
            print("   - Email: Your Moloco Publisher login email")
            print("   - Password: Your Moloco Publisher password")
            print("   - Platform ID: Found in Moloco Publisher Console URL or settings")
            print("=" * 60)
        elif "UPDATE_PASSWORD" in error_str:
            print("\n" + "=" * 60)
            print("🔐 Password Update Required:")
            print("=" * 60)
            print("Please log in to the Moloco Publisher Portal to update your password.")
            print("https://publisher.moloco.com")
            print("=" * 60)
        elif "403" in error_str or "forbidden" in error_str.lower() or "permission denied" in error_str.lower():
            print("\n" + "=" * 60)
            print("🚫 Permission Denied Error:")
            print("=" * 60)
            print("The API request was authenticated but permission was denied.")
            print("\nPossible causes:")
            print("1. Your Moloco Publisher account may not have API access enabled")
            print("2. Your account role may not have permission to use the Publisher Summary API")
            print("3. The Platform ID may be incorrect or you don't have access to it")
            print("\nTo resolve:")
            print("1. Contact Moloco support to enable API access for your account")
            print("2. Verify your Platform ID in the Moloco Publisher Console")
            print("3. Check if your account has the necessary permissions")
            print("\nMoloco Publisher Portal: https://publisher.moloco.com")
            print("=" * 60)
        elif "404" in error_str or "not found" in error_str.lower():
            print("\n" + "=" * 60)
            print("🔍 Not Found Error - Please check:")
            print("=" * 60)
            print("1. API endpoint is correct")
            print("2. Platform ID exists")
            print("=" * 60)
        elif "400" in error_str or "bad request" in error_str.lower():
            print("\n" + "=" * 60)
            print("⚠️  Bad Request Error - Please check:")
            print("=" * 60)
            print("1. Date format is correct (YYYY-MM-DD)")
            print("2. Date range is valid")
            print("3. Credentials format is correct")
            print("=" * 60)
        elif "ssl" in error_str.lower() or "certificate" in error_str.lower():
            print("\n" + "=" * 60)
            print("🔒 SSL/Connection Error - Please check:")
            print("=" * 60)
            print("1. Your network connection is working")
            print("2. No firewall/proxy blocking the connection")
            print("3. Try again later - the API endpoint might be temporarily unavailable")
            print("=" * 60)
        
        import traceback
        print("\n📋 Full traceback:")
        traceback.print_exc()


def test_raw_api_request():
    """Test raw API request to Moloco for debugging."""
    import json
    
    print("\n" + "=" * 60)
    print("MOLOCO RAW API TEST")
    print("=" * 60)
    
    # First get token
    token = test_auth_token()
    
    if not token:
        print("\n❌ Cannot proceed without token")
        return
    
    config = Config()
    moloco_config = config.get_moloco_config()
    publisher_id = moloco_config.get('publisher_id')
    
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}',
    }
    
    summary_url = 'https://sdkpubapi.moloco.com/api/adcloud/publisher/v1/sdk/summary'
    
    # Test 1: Date ranges with UTC_DATE dimension
    print("\n" + "=" * 60)
    print("TEST 1: Different date ranges with UTC_DATE")
    print("=" * 60)
    
    date_ranges = [
        ('2026-01-01', '2026-01-04'),
        ('2025-12-01', '2025-12-31'),
        ('2025-11-01', '2025-11-30'),
    ]
    
    for start, end in date_ranges:
        payload = {
            'publisher_id': publisher_id,
            'date_range': {'start': start, 'end': end},
            'dimensions': ['UTC_DATE'],
            'metrics': ['REVENUE', 'IMPRESSIONS']
        }
        
        response = requests.post(summary_url, headers=headers, json=payload, timeout=30)
        body = response.json()
        rows = body.get('rows', [])
        
        print(f"{start} to {end}: Status={response.status_code}, Rows={len(rows)}")
        if rows:
            print(f"  First row: {rows[0]}")
    
    # Test 2: Different dimensions with fixed date range
    print("\n" + "=" * 60)
    print("TEST 2: Different dimensions (2025-12-01 to 2025-12-31)")
    print("=" * 60)
    
    dimensions_list = [
        ['UTC_DATE'],
        ['AD_UNIT_ID'],
        ['PUBLISHER_APP_ID'],
        ['PUBLISHER_APP_STORE_ID'],
        ['GEO_COUNTRY'],
        ['DEVICE_OS'],
    ]
    
    for dims in dimensions_list:
        payload = {
            'publisher_id': publisher_id,
            'date_range': {'start': '2025-12-01', 'end': '2025-12-31'},
            'dimensions': dims,
            'metrics': ['REVENUE', 'IMPRESSIONS']
        }
        
        response = requests.post(summary_url, headers=headers, json=payload, timeout=30)
        body = response.json()
        rows = body.get('rows', [])
        
        dim_str = str(dims)
        print(f"Dimensions {dim_str}: Status={response.status_code}, Rows={len(rows)}")
        if rows:
            metric = rows[0].get('metric', {})
            print(f"  Revenue: ${metric.get('revenue', 0):.2f}, Impressions: {metric.get('impressions', 0)}")
        if body.get('code'):
            print(f"  Error: {body.get('message', body)}")
    
    # Test 3: Different metrics
    print("\n" + "=" * 60)
    print("TEST 3: Different metrics (2025-12-01 to 2025-12-31)")
    print("=" * 60)
    
    metrics_list = [
        ['REVENUE'],
        ['IMPRESSIONS'],
        ['REQUESTS'],
        ['CLICKS'],
        ['REVENUE', 'IMPRESSIONS', 'REQUESTS', 'CLICKS'],
    ]
    
    for mets in metrics_list:
        payload = {
            'publisher_id': publisher_id,
            'date_range': {'start': '2025-12-01', 'end': '2025-12-31'},
            'dimensions': ['UTC_DATE'],
            'metrics': mets
        }
        
        response = requests.post(summary_url, headers=headers, json=payload, timeout=30)
        body = response.json()
        rows = body.get('rows', [])
        
        print(f"Metrics {mets}: Status={response.status_code}, Rows={len(rows)}")
        if rows:
            print(f"  First row metric: {rows[0].get('metric', {})}")
        if body.get('code'):
            print(f"  Error: {body.get('message', body)}")



if __name__ == "__main__":
    test_moloco_fetcher()
    
    # Uncomment to test auth token only
    # test_auth_token()
    
    # Uncomment to test raw API request for debugging
    # test_raw_api_request()

