"""
Test script for [NetworkName] fetcher.
Async version with full test capabilities.
API Docs: [API_DOCUMENTATION_URL]

Usage:
    1. Update config.yaml with credentials
    2. Run: python test_networkname.py
    3. Optional args:
       --auth-only     Only test authentication
       --full-fetch    Run full fetch (default: auth + report test)
"""
import sys
import io
import json
import asyncio
from datetime import datetime, timedelta, timezone

# Fix console encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from src.config import Config

# UPDATE THIS IMPORT
from src.fetchers.networkname_fetcher import NetworkNameFetcher


def print_separator(title: str = "", char: str = "="):
    """Print a separator line."""
    print(f"\n{char*60}")
    if title:
        print(f"  {title}")
        print(f"{char*60}")


def check_credentials(config: dict) -> bool:
    """
    Check if credentials are properly configured.
    Returns True if valid, False otherwise.
    """
    print_separator("🔍 CREDENTIAL CHECK")
    
    is_valid = True
    required_fields = ['api_key', 'publisher_id']  # UPDATE BASED ON NETWORK
    
    for field in required_fields:
        value = config.get(field, '')
        
        # Check for placeholder values
        if not value:
            print(f"   ❌ {field}: MISSING")
            is_valid = False
        elif value.startswith("YOUR_") or value == "":
            print(f"   ❌ {field}: PLACEHOLDER - please update config.yaml")
            is_valid = False
        else:
            # Mask sensitive values
            if any(s in field.lower() for s in ['key', 'token', 'password', 'secret']):
                display_value = f"{'*' * min(len(value), 10)}... ({len(value)} chars)"
            else:
                display_value = value
            print(f"   ✅ {field}: {display_value}")
    
    return is_valid


def print_results(data: dict):
    """Print fetched data in a readable format."""
    print_separator("📊 FETCH RESULTS")
    
    print(f"\n   Network: {data.get('network', 'Unknown')}")
    print(f"   Date Range: {data.get('date_range', {}).get('start')} to {data.get('date_range', {}).get('end')}")
    
    print(f"\n   💰 TOTALS:")
    print(f"      Revenue: ${data.get('revenue', 0):.2f}")
    print(f"      Impressions: {data.get('impressions', 0):,}")
    print(f"      eCPM: ${data.get('ecpm', 0):.2f}")
    
    print(f"\n   📱 PLATFORM BREAKDOWN:")
    for platform in ['android', 'ios']:
        pdata = data.get('platform_data', {}).get(platform, {})
        revenue = pdata.get('revenue', 0)
        impressions = pdata.get('impressions', 0)
        ecpm = pdata.get('ecpm', 0)
        
        if impressions > 0:
            print(f"\n      {platform.upper()}:")
            print(f"         Revenue: ${revenue:.2f}")
            print(f"         Impressions: {impressions:,}")
            print(f"         eCPM: ${ecpm:.2f}")
            
            print(f"\n         Ad Types:")
            for ad_type in ['banner', 'interstitial', 'rewarded']:
                adata = pdata.get('ad_data', {}).get(ad_type, {})
                if adata.get('impressions', 0) > 0:
                    print(f"            {ad_type}: ${adata.get('revenue', 0):.2f} / {adata.get('impressions', 0):,} impr / ${adata.get('ecpm', 0):.2f} eCPM")


async def main():
    """Main async test function."""
    print_separator("🧪 NETWORKNAME FETCHER TEST (ASYNC)", "=")
    
    # Parse command line arguments
    auth_only = '--auth-only' in sys.argv
    full_fetch = '--full-fetch' in sys.argv
    
    # ========================================
    # Step 1: Load Configuration
    # ========================================
    print_separator("📋 CONFIGURATION")
    
    config = Config()
    network_config = config.get_networkname_config()  # UPDATE THIS METHOD NAME
    
    print(f"\n   Config loaded:")
    for key, value in network_config.items():
        if any(s in key.lower() for s in ['key', 'token', 'password', 'secret']):
            print(f"      {key}: {'*' * 10}")
        else:
            print(f"      {key}: {value}")
    
    if not network_config.get('enabled', False):
        print("\n   ❌ Network is disabled in config.yaml")
        print("      Set 'enabled: true' to run tests")
        return
    
    # ========================================
    # Step 2: Check Credentials
    # ========================================
    if not check_credentials(network_config):
        print("\n   ❌ Please update credentials in config.yaml")
        return
    
    # ========================================
    # Step 3: Initialize Fetcher
    # ========================================
    print_separator("🔧 INITIALIZE FETCHER")
    
    # UPDATE THESE PARAMETERS BASED ON NETWORK
    fetcher = NetworkNameFetcher(
        api_key=network_config['api_key'],
        publisher_id=network_config['publisher_id'],
        app_ids=network_config.get('app_ids'),
    )
    
    print(f"   ✅ Fetcher initialized: {fetcher.get_network_name()}")
    print(f"   ✅ Network enum: {fetcher.get_network_enum()}")
    
    try:
        # ========================================
        # Step 4: Auth Test
        # ========================================
        if hasattr(fetcher, '_test_auth'):
            auth_success = await fetcher._test_auth()
            
            if not auth_success:
                print("\n   ❌ Auth test failed - fix credentials before continuing")
                return
            
            if auth_only:
                print("\n   ✅ Auth test passed (--auth-only mode)")
                return
        
        # ========================================
        # Step 5: Report Test
        # ========================================
        end_date = datetime.now(timezone.utc) - timedelta(days=1)
        start_date = end_date
        
        print(f"\n📅 Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        if hasattr(fetcher, '_test_report_request') and not full_fetch:
            # Debug mode - use test method
            response_data = await fetcher._test_report_request(start_date, end_date)
            
            if response_data:
                print("\n" + "="*60)
                print("📋 RESPONSE STRUCTURE ANALYSIS")
                print("="*60)
                
                def analyze_structure(obj, prefix=""):
                    if isinstance(obj, dict):
                        for key, value in obj.items():
                            print(f"{prefix}{key}: {type(value).__name__}")
                            if isinstance(value, (dict, list)) and value:
                                analyze_structure(value, prefix + "  ")
                    elif isinstance(obj, list) and obj:
                        print(f"{prefix}[0]: {type(obj[0]).__name__}")
                        if isinstance(obj[0], dict):
                            analyze_structure(obj[0], prefix + "  ")
                
                analyze_structure(response_data)
        else:
            # Full fetch mode
            print_separator("🚀 FULL DATA FETCH")
            
            data = await fetcher.fetch_data(start_date, end_date)
            print_results(data)
        
        print_separator("✅ TEST COMPLETED SUCCESSFULLY", "=")
        
    except Exception as e:
        print_separator("❌ TEST FAILED", "=")
        print(f"\n   Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # ⚠️ Important: Close the aiohttp session
        await fetcher.close()
        print("\n   🔒 Session closed")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
