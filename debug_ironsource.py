"""Debug script to check IronSource daily breakdown"""
import asyncio
from datetime import datetime, timedelta, timezone
from src.config import Config

async def main():
    config = Config()
    
    now = datetime.now(timezone.utc)
    end_date = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    start_date = end_date - timedelta(days=6)
    
    print(f'Date range: {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}')
    
    networks_config = config.config.get('networks', {})
    ironsource_config = networks_config.get('ironsource', {})
    
    if ironsource_config.get('enabled'):
        from src.fetchers.ironsource_fetcher import IronSourceFetcher
        fetcher = IronSourceFetcher(
            username=ironsource_config.get('username'),
            secret_key=ironsource_config.get('secret_key'),
            android_app_keys=ironsource_config.get('android_app_keys', []),
            ios_app_keys=ironsource_config.get('ios_app_keys', [])
        )
        
        # Direct API call to see raw response structure
        print("\n=== Raw API Response ===")
        
        android_keys = ironsource_config.get('android_app_keys', [])
        headers = fetcher._get_auth_headers()
        params = {
            'startDate': start_date.strftime('%Y-%m-%d'),
            'endDate': end_date.strftime('%Y-%m-%d'),
            'appKey': ','.join(android_keys),
            'adUnits': fetcher.SUPPORTED_AD_UNITS,
            'metrics': 'revenue,impressions,eCPM',
            'breakdown': 'adUnits,date',
        }
        
        url = f"{fetcher.BASE_URL}{fetcher.REPORT_ENDPOINT}"
        print(f"Request URL: {url}")
        print(f"Request params: {params}")
        
        data = await fetcher._get_json(url, headers=headers, params=params)
        
        print(f"\nResponse type: {type(data)}")
        if isinstance(data, list):
            print(f"Number of adUnit items: {len(data)}")
            for item in data:
                ad_unit = item.get('adUnits', 'Unknown')
                metrics_list = item.get('data', [])
                print(f"\n--- {ad_unit} ({len(metrics_list)} data entries) ---")
                for i, m in enumerate(metrics_list[:3]):  # First 3
                    print(f"  [{i}] date='{m.get('date')}' rev={m.get('revenue')} imps={m.get('impressions')}")
                if len(metrics_list) > 3:
                    print(f"  ... and {len(metrics_list) - 3} more entries")
        else:
            print(f"Unexpected response: {data}")
        
        await fetcher.close()

if __name__ == "__main__":
    asyncio.run(main())
