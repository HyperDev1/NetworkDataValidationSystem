"""
Test script for Meta Audience Network fetcher.
Tests the daily data fetching approach.

Usage:
    python test_meta.py                     # Test default (last 7 days)
    python test_meta.py --date 2026-01-16   # Test specific date
    python test_meta.py --range 2026-01-10 2026-01-18  # Test date range
"""
import argparse
import asyncio
import requests
from datetime import datetime, timedelta, timezone
from src.config import Config
from src.fetchers import MetaFetcher


def check_token_info(access_token: str):
    """Check token info and permissions."""
    print("\n🔍 Checking token info...")
    
    url = "https://graph.facebook.com/v24.0/me"
    params = {"access_token": access_token, "fields": "id,name"}
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        print(f"   Token User/App ID: {data.get('id')}")
        print(f"   Token Name: {data.get('name')}")
    else:
        print(f"   ❌ Token check failed: {response.text[:200]}")


def test_meta_fetcher(start_date: datetime = None, end_date: datetime = None):
    """Test Meta Audience Network fetcher with date range."""
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
    
    # Calculate date range
    now_utc = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    if end_date is None:
        end_date = now_utc

    if start_date is None:
        start_date = end_date - timedelta(days=7)
   
    
    print(f"\n📅 Requesting Meta data:")
    print(f"   Start date: {start_date.strftime('%Y-%m-%d')}")
    print(f"   End date: {end_date.strftime('%Y-%m-%d')}")
    print(f"   Today: {now_utc.strftime('%Y-%m-%d')}")
    print(f"   Days from today: T-{(now_utc - end_date).days} to T-{(now_utc - start_date).days}")
    
    # Fetch data
    print(f"\n📥 Fetching data...")
    try:
        data = asyncio.run(fetcher.fetch_data(start_date, end_date))
        
        print(f"\n✅ SUCCESS!")
        print(f"\n📊 Results:")
        print(f"   Total Revenue: ${data['revenue']:.2f}")
        print(f"   Total Impressions: {data['impressions']:,}")
        print(f"   Total eCPM: ${data['ecpm']:.2f}")
        
        # Daily breakdown
        daily_data = data.get('daily_data', {})
        if daily_data:
            print(f"\n📅 Daily Breakdown ({len(daily_data)} days with data):")
            for date_key in sorted(daily_data.keys()):
                day_data = daily_data[date_key]
                total_rev = sum(
                    ad.get('revenue', 0) 
                    for plat in day_data.values() 
                    for ad in plat.values()
                )
                total_imp = sum(
                    ad.get('impressions', 0) 
                    for plat in day_data.values() 
                    for ad in plat.values()
                )
                print(f"   {date_key}: ${total_rev:.2f} rev, {total_imp:,} imp")
            
            # Check which dates are missing
            requested_dates = set()
            current = start_date
            while current <= end_date:
                requested_dates.add(current.strftime('%Y-%m-%d'))
                current += timedelta(days=1)
            
            received_dates = set(daily_data.keys())
            missing_dates = requested_dates - received_dates
            
            if missing_dates:
                print(f"\n⚠️ Missing dates ({len(missing_dates)}):")
                for d in sorted(missing_dates):
                    print(f"   - {d}")
                
                # Find the last available date
                if received_dates:
                    last_available = max(received_dates)
                    last_available_dt = datetime.strptime(last_available, '%Y-%m-%d')
                    delay_days = (now_utc.replace(tzinfo=None) - last_available_dt).days
                    print(f"\n📊 Data availability:")
                    print(f"   Last available date: {last_available}")
                    print(f"   Actual delay: T-{delay_days} (data is {delay_days} days behind)")
        
        print(f"\n📱 Platform Breakdown:")
        for platform, pdata in data['platform_data'].items():
            if pdata['impressions'] > 0:
                print(f"\n   {platform.upper()}:")
                print(f"      Revenue: ${pdata['revenue']:.2f}")
                print(f"      Impressions: {pdata['impressions']:,}")
                print(f"      eCPM: ${pdata['ecpm']:.2f}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if hasattr(fetcher, 'close'):
            asyncio.run(fetcher.close())


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(description='Test Meta Audience Network fetcher')
    parser.add_argument('--date', type=str, help='Single date to test (YYYY-MM-DD)')
    parser.add_argument('--range', nargs=2, type=str, metavar=('START', 'END'),
                        help='Date range to test (YYYY-MM-DD YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    start_date = None
    end_date = None
    
    if args.date:
        single_date = datetime.strptime(args.date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        start_date = single_date
        end_date = single_date
    elif args.range:
        start_date = datetime.strptime(args.range[0], '%Y-%m-%d').replace(tzinfo=timezone.utc)
        end_date = datetime.strptime(args.range[1], '%Y-%m-%d').replace(tzinfo=timezone.utc)
    
    test_meta_fetcher(start_date, end_date)


if __name__ == "__main__":
    main()

