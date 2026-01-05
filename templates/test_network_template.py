"""
Test script for [NetworkName] fetcher.
API Docs: [API_DOCUMENTATION_URL]

Usage:
    1. Update config.yaml with credentials
    2. Run: python test_networkname.py
"""
import sys
import io
import json
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


def main():
    print_separator("🧪 NETWORKNAME FETCHER TEST", "=")
    
    # ========================================
    # Step 1: Load Configuration
    # ========================================
    print_separator("📋 CONFIGURATION")
    
    try:
        config = Config()
        network_config = config.get_networkname_config()  # UPDATE METHOD NAME
    except FileNotFoundError as e:
        print(f"   ❌ Config file not found: {e}")
        return
    except Exception as e:
        print(f"   ❌ Config load error: {e}")
        return
    
    print(f"   Config loaded successfully")
    print(f"\n   Settings:")
    for key, value in network_config.items():
        if any(s in key.lower() for s in ['key', 'token', 'password', 'secret']):
            print(f"      {key}: {'*' * 10}")
        else:
            print(f"      {key}: {value}")
    
    # ========================================
    # Step 2: Check if enabled
    # ========================================
    if not network_config.get('enabled'):
        print(f"\n   ⚠️ Network is DISABLED in config.yaml")
        print(f"   Set 'enabled: true' to test")
        return
    
    # ========================================
    # Step 3: Validate Credentials
    # ========================================
    if not check_credentials(network_config):
        print(f"\n   ❌ Please update config.yaml with valid credentials")
        return
    
    # ========================================
    # Step 4: Initialize Fetcher
    # ========================================
    print_separator("🔧 INITIALIZING FETCHER")
    
    try:
        fetcher = NetworkNameFetcher(
            api_key=network_config['api_key'],
            publisher_id=network_config['publisher_id'],
            # ADD OTHER PARAMETERS AS NEEDED
        )
        print(f"   ✅ Fetcher initialized")
    except Exception as e:
        print(f"   ❌ Initialization error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # ========================================
    # Step 5: Auth Test (Optional - comment out if API doesn't have auth endpoint)
    # ========================================
    print_separator("🔐 AUTH TEST")
    
    auth_success = fetcher._test_auth()
    
    if not auth_success:
        print(f"\n   ❌ Auth test failed - check credentials")
        print(f"\n   💡 Common issues:")
        print(f"      - Invalid API key")
        print(f"      - Missing permissions")
        print(f"      - Wrong endpoint URL")
        return
    
    print(f"\n   ✅ Auth test passed")
    
    # ========================================
    # Step 6: Report Request Test
    # ========================================
    # Set date range (yesterday for data availability)
    end_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    start_date = end_date  # Single day
    
    print_separator("📊 REPORT REQUEST TEST")
    print(f"   Date: {start_date.strftime('%Y-%m-%d')}")
    
    response_data = fetcher._test_report_request(start_date, end_date)
    
    if not response_data:
        print(f"\n   ❌ Report request failed")
        print(f"\n   💡 Common issues:")
        print(f"      - Wrong date format")
        print(f"      - Data not available yet (try older date)")
        print(f"      - Missing required parameters")
        return
    
    # ========================================
    # Step 7: Analyze Response Structure
    # ========================================
    print_separator("🔍 RESPONSE STRUCTURE ANALYSIS")
    
    def analyze_structure(obj, prefix="", max_depth=3, current_depth=0):
        """Recursively analyze and print object structure."""
        if current_depth >= max_depth:
            return
        
        if isinstance(obj, dict):
            for key, value in list(obj.items())[:10]:  # Limit to first 10 keys
                value_type = type(value).__name__
                if isinstance(value, (dict, list)):
                    print(f"{prefix}{key}: {value_type}")
                    analyze_structure(value, prefix + "  ", max_depth, current_depth + 1)
                else:
                    # Show sample value
                    sample = str(value)[:50]
                    print(f"{prefix}{key}: {value_type} = {sample}")
        elif isinstance(obj, list) and obj:
            print(f"{prefix}[0]: {type(obj[0]).__name__} (list of {len(obj)} items)")
            if isinstance(obj[0], dict):
                analyze_structure(obj[0], prefix + "  ", max_depth, current_depth + 1)
    
    analyze_structure(response_data)
    
    # ========================================
    # Step 8: Full Data Fetch Test
    # ========================================
    print_separator("🚀 FULL DATA FETCH TEST")
    
    try:
        data = fetcher.fetch_data(start_date, end_date)
        print_results(data)
        
        # Validation
        print_separator("✅ VALIDATION")
        
        issues = []
        
        if data['revenue'] <= 0:
            issues.append("Revenue is 0 or negative")
        
        if data['impressions'] <= 0:
            issues.append("Impressions is 0 or negative")
        
        if data['ecpm'] < 0.01 or data['ecpm'] > 100:
            issues.append(f"eCPM seems unusual: ${data['ecpm']:.2f}")
        
        # Check platform totals
        android_rev = data['platform_data']['android']['revenue']
        ios_rev = data['platform_data']['ios']['revenue']
        total_platform_rev = android_rev + ios_rev
        
        if abs(total_platform_rev - data['revenue']) > 0.01:
            issues.append(f"Platform sum ({total_platform_rev:.2f}) != Total ({data['revenue']:.2f})")
        
        if issues:
            print(f"\n   ⚠️ Potential issues:")
            for issue in issues:
                print(f"      - {issue}")
        else:
            print(f"\n   ✅ All validations passed!")
        
    except Exception as e:
        print(f"\n   ❌ Fetch error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # ========================================
    # Final Summary
    # ========================================
    print_separator("🎉 TEST COMPLETE", "=")
    print(f"\n   Network: {data.get('network')}")
    print(f"   Revenue: ${data.get('revenue', 0):.2f}")
    print(f"   Impressions: {data.get('impressions', 0):,}")
    print(f"\n   Next steps:")
    print(f"   1. Verify values match network dashboard")
    print(f"   2. Update validation_service.py if needed")
    print(f"   3. Run full system test: python main.py")


if __name__ == "__main__":
    main()
