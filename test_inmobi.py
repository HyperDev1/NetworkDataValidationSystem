"""
InMobi Data Fetcher Test Script.
Tests the InMobi Publisher Reporting API integration.
API Docs: https://support.inmobi.com/monetize/inmobi-apis/reporting-api
"""
import sys
from datetime import datetime, timedelta, timezone
from src.config import Config
from src.fetchers import InMobiFetcher


def test_inmobi_fetcher():
    """Test InMobi data fetching."""
    print("=" * 60)
    print("INMOBI DATA FETCHER TEST")
    print("=" * 60)
    
    # Load configuration
    try:
        config = Config()
        print("[OK] Configuration loaded successfully")
    except Exception as e:
        print(f"[ERROR] Failed to load configuration: {str(e)}")
        return
    
    # Get InMobi config
    inmobi_config = config.get_inmobi_config()
    
    if not inmobi_config:
        print("\n[WARN] InMobi configuration not found in config.yaml")
        print("   Please add the following to config.yaml under 'networks':")
        print("""
  inmobi:
    enabled: true
    account_id: "YOUR_ACCOUNT_ID"
    api_key: "YOUR_API_KEY"
""")
        return
    
    if not inmobi_config.get('enabled'):
        print("[WARN] InMobi is disabled in config.yaml")
        print("   Set 'enabled: true' under networks.inmobi to enable")
        return
    
    print(f"\nInMobi Configuration:")
    print(f"   Enabled: {inmobi_config.get('enabled')}")
    print(f"   Account ID: {inmobi_config.get('account_id')}")
    print(f"   Username: {inmobi_config.get('username', 'N/A')}")
    print(f"   Secret Key: {inmobi_config.get('secret_key', '')[:30]}...")
    
    # Check required fields
    account_id = inmobi_config.get('account_id')
    secret_key = inmobi_config.get('secret_key')
    username = inmobi_config.get('username')
    
    if not account_id:
        print("\n[ERROR] Account ID is missing")
        return
    
    if not secret_key:
        print("\n[ERROR] Secret Key is missing")
        print("   Please get your Secret Key from:")
        print("   https://publisher.inmobi.com -> Account Settings -> API Key")
        return
    
    # Initialize fetcher
    print(f"\nInitializing InMobiFetcher...")
    try:
        fetcher = InMobiFetcher(
            account_id=account_id,
            secret_key=secret_key,
            username=username
        )
        print(f"   Network name: {fetcher.get_network_name()}")
    except Exception as e:
        print(f"   [ERROR] Failed to initialize fetcher: {str(e)}")
        import traceback
        traceback.print_exc()
        return
    
    # InMobi typically has 1-2 day reporting delay
    now_utc = datetime.now(timezone.utc)
    inmobi_delay_days = 2
    end_date = now_utc.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=inmobi_delay_days)
    start_date = end_date
    
    print(f"\nRequesting InMobi data for: {start_date.strftime('%Y-%m-%d')} (UTC)")
    print(f"   (This is {inmobi_delay_days} days ago - InMobi's expected data availability)")
    
    # Fetch data
    print(f"\nFetching data...")
    try:
        data = fetcher.fetch_data(start_date, end_date)
        
        print(f"\n[SUCCESS]")
        print(f"\nResults:")
        print(f"   Total Revenue: ${data['revenue']:.2f}")
        print(f"   Total Impressions: {data['impressions']:,}")
        print(f"   Total eCPM: ${data['ecpm']:.2f}")
        
        print(f"\nPlatform Breakdown:")
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
        
        # Write output to file for debugging
        with open("inmobi_output.txt", "w", encoding="utf-8") as f:
            f.write(f"InMobi Data Fetch Results\n")
            f.write(f"========================\n")
            f.write(f"Date Range: {data['date_range']['start']} to {data['date_range']['end']}\n")
            f.write(f"Total Revenue: ${data['revenue']:.2f}\n")
            f.write(f"Total Impressions: {data['impressions']:,}\n")
            f.write(f"Total eCPM: ${data['ecpm']:.2f}\n\n")
            
            for platform, pdata in data['platform_data'].items():
                f.write(f"\n{platform.upper()}:\n")
                f.write(f"  Revenue: ${pdata['revenue']:.2f}\n")
                f.write(f"  Impressions: {pdata['impressions']:,}\n")
                f.write(f"  eCPM: ${pdata['ecpm']:.2f}\n")
                
                for ad_type, ad_data in pdata['ad_data'].items():
                    f.write(f"  {ad_type}: ${ad_data['revenue']:.2f} | {ad_data['impressions']:,} imps | ${ad_data['ecpm']:.2f} eCPM\n")
        
        print(f"\nResults saved to inmobi_output.txt")
        
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()


def test_inmobi_raw_request():
    """Test raw InMobi API request to debug authentication."""
    print("\n" + "=" * 60)
    print("INMOBI RAW API REQUEST TEST")
    print("=" * 60)
    
    import requests
    
    # Load configuration
    try:
        config = Config()
        inmobi_config = config.get_inmobi_config()
        
        if not inmobi_config or not inmobi_config.get('enabled'):
            print("[WARN] InMobi not configured or disabled")
            return
        
        account_id = inmobi_config.get('account_id')
        api_key = inmobi_config.get('api_key')
        
        print(f"\nTesting raw API request...")
        print(f"   Account ID: {account_id}")
        print(f"   API Key: {api_key[:30]}...")
        
        # Test dates (2 days ago)
        now_utc = datetime.now(timezone.utc)
        test_date = (now_utc - timedelta(days=2)).strftime("%Y-%m-%d")
        
        # Request headers
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "accountId": account_id,
            "secretKey": api_key
        }
        
        # Request body
        body = {
            "reportRequest": {
                "metrics": ["adImpressions", "earnings"],
                "timeFrame": test_date,
                "endDate": test_date,
                "groupBy": ["platform", "adType"],
                "filterBy": {},
                "orderBy": [],
                "orderType": ""
            }
        }
        
        print(f"\nRequest URL: https://api.inmobi.com/v3.0/reporting/publisher")
        print(f"Request Headers: {headers}")
        print(f"Request Body: {body}")
        
        response = requests.post(
            "https://api.inmobi.com/v3.0/reporting/publisher",
            json=body,
            headers=headers,
            timeout=60
        )
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")
        
    except Exception as e:
        print(f"\n[ERROR] Raw request failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run main test
    test_inmobi_fetcher()
    
    # Uncomment to test raw API request
    # test_inmobi_raw_request()
