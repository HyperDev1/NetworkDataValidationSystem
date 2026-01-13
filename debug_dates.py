"""Debug script to check date matching between MAX and network data"""
import asyncio
from datetime import datetime, timedelta, timezone
from src.config import Config
from src.fetchers.factory import FetcherFactory

async def main():
    config = Config()
    
    now = datetime.now(timezone.utc)
    end_date = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    start_date = end_date - timedelta(days=6)
    
    print(f'Date range: {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}')
    
    # Test Moloco
    print("\n" + "="*60)
    print("MOLOCO - Raw API Response")
    print("="*60)
    
    networks_config = config.config.get('networks', {})
    moloco_config = networks_config.get('moloco', {})
    
    if moloco_config.get('enabled'):
        from src.fetchers.moloco_fetcher import MolocoFetcher
        moloco_fetcher = MolocoFetcher(
            email=moloco_config.get('email'),
            password=moloco_config.get('password'),
            platform_id=moloco_config.get('platform_id'),
            publisher_id=moloco_config.get('publisher_id'),
            ad_unit_mapping=moloco_config.get('ad_unit_mapping', {}),
            app_bundle_ids=moloco_config.get('app_bundle_ids', [])
        )
        
        # Make raw API request
        payload = {
            'publisher_id': moloco_fetcher.publisher_id,
            'date_range': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            },
            'dimensions': ['UTC_DATE', 'DEVICE_OS', 'AD_UNIT_ID'],
            'metrics': ['REVENUE', 'IMPRESSIONS', 'REQUESTS', 'FILLS', 'CLICKS'],
        }
        
        if moloco_fetcher.app_bundle_ids:
            payload['dimension_filters'] = [
                {
                    'dimension': 'PUBLISHER_APP_STORE_ID',
                    'values': moloco_fetcher.app_bundle_ids
                }
            ]
        
        response_data = await moloco_fetcher._make_request(payload)
        
        rows = response_data.get('rows', [])
        print(f"\nTotal rows: {len(rows)}")
        print(f"\nFirst 5 rows (raw):")
        for row in rows[:5]:
            print(f"  Keys: {row.keys()}")
            print(f"  Row: {row}")
        
        await moloco_fetcher.close()
    
    # Test IronSource
    print("\n" + "="*60)
    print("IRONSOURCE - Raw API Response")
    print("="*60)
    
    ironsource_config = networks_config.get('ironsource', {})
    
    if ironsource_config.get('enabled'):
        from src.fetchers.ironsource_fetcher import IronSourceFetcher
        ironsource_fetcher = IronSourceFetcher(
            username=ironsource_config.get('username'),
            secret_key=ironsource_config.get('secret_key'),
            android_app_keys=ironsource_config.get('android_app_keys', []),
            ios_app_keys=ironsource_config.get('ios_app_keys', [])
        )
        
        # Make raw API request
        headers = ironsource_fetcher._get_auth_headers()
        params = {
            'startDate': start_date.strftime('%Y-%m-%d'),
            'endDate': end_date.strftime('%Y-%m-%d'),
            'appKey': ','.join(ironsource_config.get('android_app_keys', [])),
            'adUnits': ironsource_fetcher.SUPPORTED_AD_UNITS,
            'metrics': 'revenue,impressions,eCPM,clicks,appRequests,appFills',
            'breakdown': 'adUnits,date',
        }
        
        url = f"{ironsource_fetcher.BASE_URL}{ironsource_fetcher.REPORT_ENDPOINT}"
        data = await ironsource_fetcher._get_json(url, headers=headers, params=params)
        
        print(f"\nResponse type: {type(data)}")
        if isinstance(data, list):
            print(f"Total items: {len(data)}")
            if len(data) > 0:
                item = data[0]
                print(f"\nFirst item keys: {item.keys() if isinstance(item, dict) else 'N/A'}")
                print(f"First item: {item}")
                if 'data' in item:
                    metrics = item.get('data', [])
                    print(f"\nMetrics list ({len(metrics)} items):")
                    for m in metrics[:5]:
                        print(f"  {m}")
        
        await ironsource_fetcher.close()

if __name__ == "__main__":
    asyncio.run(main())
