"""
AdMob Data Fetcher Test Script.
Tests the AdMob API integration.
"""
import sys
import io
from datetime import datetime, timedelta
from src.config import Config
from src.fetchers import AdmobFetcher

# Fix console encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def main():
    """Test AdMob data fetching."""
    print("=" * 60)
    print("AdMob Data Fetcher Test")
    print("=" * 60)
    
    # Load configuration
    try:
        config = Config()
        print("[OK] Configuration loaded successfully")
    except Exception as e:
        print(f"[ERROR] Failed to load configuration: {str(e)}")
        return
    
    # Get AdMob config
    admob_config = config.get_admob_config()
    
    if not admob_config.get('enabled'):
        print("[WARN] AdMob is disabled in config.yaml")
        print("   Set 'enabled: true' under networks.admob to enable")
        return
    
    print(f"\n[INFO] AdMob Configuration:")
    print(f"   Service Account: {admob_config.get('service_account_json_path')}")
    print(f"   Publisher ID: {admob_config.get('publisher_id')}")
    print(f"   App IDs: {admob_config.get('app_ids', 'All apps')}")
    
    # Initialize fetcher
    print(f"\n[INFO] Initializing AdMob fetcher...")
    try:
        fetcher = AdmobFetcher(
            service_account_json_path=admob_config['service_account_json_path'],
            publisher_id=admob_config['publisher_id'],
            app_ids=admob_config.get('app_ids')
        )
        print("[OK] AdMob fetcher initialized successfully")
    except ImportError as e:
        print(f"[ERROR] Missing dependencies: {str(e)}")
        print("\n   Install required packages:")
        print("   pip install google-auth google-api-python-client")
        return
    except FileNotFoundError as e:
        print(f"[ERROR] Service account file not found: {str(e)}")
        print("\n   Please ensure the service account JSON file exists at the specified path")
        return
    except Exception as e:
        print(f"[ERROR] Failed to initialize AdMob fetcher: {str(e)}")
        return
    
    # Set date range (yesterday, as today's data may not be available)
    end_date = datetime.utcnow() - timedelta(days=1)
    start_date = end_date  # Single day
    
    print(f"\n[INFO] Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Fetch data
    print(f"\n[INFO] Fetching AdMob data...")
    try:
        data = fetcher.fetch_data(start_date, end_date)
        print("[OK] Data fetched successfully!")
        
        # Display results
        print(f"\n{'=' * 60}")
        print("AdMob Data Summary")
        print("=" * 60)
        
        print(f"\nTotal Revenue: ${data['revenue']:.2f}")
        print(f"Total Impressions: {data['impressions']:,}")
        print(f"Total eCPM: ${data['ecpm']:.2f}")
        
        # Platform breakdown
        print(f"\n{'-' * 40}")
        print("Platform Breakdown:")
        print("-" * 40)
        
        for platform in ['android', 'ios']:
            p_data = data['platform_data'][platform]
            if p_data['impressions'] > 0:
                print(f"\n  {platform.upper()}:")
                print(f"    Revenue: ${p_data['revenue']:.2f}")
                print(f"    Impressions: {p_data['impressions']:,}")
                print(f"    eCPM: ${p_data['ecpm']:.2f}")
                
                # Ad type breakdown
                print(f"\n    Ad Types:")
                for ad_type in ['banner', 'interstitial', 'rewarded']:
                    ad_data = p_data['ad_data'][ad_type]
                    if ad_data['impressions'] > 0:
                        print(f"      {ad_type.capitalize()}:")
                        print(f"        Revenue: ${ad_data['revenue']:.2f}")
                        print(f"        Impressions: {ad_data['impressions']:,}")
                        print(f"        eCPM: ${ad_data['ecpm']:.2f}")
        
        print(f"\n{'=' * 60}")
        print("[OK] AdMob test completed successfully!")
        
    except Exception as e:
        error_str = str(e)
        print(f"[ERROR] Error fetching data: {error_str}")
        
        # Provide helpful error messages
        if "401" in error_str or "authentication credential" in error_str.lower():
            print("\n" + "=" * 60)
            print("[HELP] Authentication Error - Please check:")
            print("=" * 60)
            print("1. AdMob API is enabled in Google Cloud Console:")
            print("   https://console.cloud.google.com/apis/library/admob.googleapis.com")
            print("")
            print("2. Service Account has been invited to AdMob:")
            print("   - Go to: https://apps.admob.com")
            print("   - Settings -> Access & Authorization -> Users")
            print("   - Click 'Invite new user'")
            print("   - Enter Service Account email from JSON file")
            print("=" * 60)
        elif "404" in error_str or "not found" in error_str.lower():
            print("\n" + "=" * 60)
            print("[HELP] Entity Not Found - Please check:")
            print("=" * 60)
            print("1. Publisher ID is correct in config.yaml")
            print("2. Service Account has access to this AdMob account")
            print("=" * 60)
        
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

