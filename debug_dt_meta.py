"""Debug DT Exchange and Meta daily data."""
import asyncio
from datetime import datetime, timedelta
from src.fetchers.dt_exchange_fetcher import DTExchangeFetcher
from src.fetchers.meta_fetcher import MetaFetcher
from src.config import Config

config = Config()

async def test_dt_exchange():
    print("=" * 60)
    print("DT Exchange Daily Data Debug")
    print("=" * 60)
    
    networks_cfg = config.get_networks_config()
    cfg = networks_cfg.get('dt_exchange', {})
    # Remove non-fetcher keys
    allowed_keys = ['client_id', 'client_secret', 'source', 'app_ids']
    cfg = {k: v for k, v in cfg.items() if k in allowed_keys}
    fetcher = DTExchangeFetcher(**cfg)
    
    end_date = datetime(2026, 1, 12)
    start_date = end_date - timedelta(days=6)
    
    result = await fetcher.fetch_data(start_date, end_date)
    daily = result.get('daily_data', {})
    
    print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"Total dates found: {len(daily)}")
    print()
    
    for date_key in sorted(daily.keys()):
        platforms = daily[date_key]
        total_imps = 0
        total_rev = 0
        for plat, ad_types in platforms.items():
            for ad_type, metrics in ad_types.items():
                total_imps += metrics.get('impressions', 0)
                total_rev += metrics.get('revenue', 0)
        print(f"{date_key}: {total_imps:,} impressions, ${total_rev:.2f}")


async def test_meta():
    print()
    print("=" * 60)
    print("Meta Daily Data Debug")
    print("=" * 60)
    
    networks_cfg = config.get_networks_config()
    cfg = networks_cfg.get('meta', {})
    # Remove non-fetcher keys
    allowed_keys = ['access_token', 'business_id']
    cfg = {k: v for k, v in cfg.items() if k in allowed_keys}
    fetcher = MetaFetcher(**cfg)
    
    end_date = datetime(2026, 1, 12)
    start_date = end_date - timedelta(days=6)
    
    result = await fetcher.fetch_data(start_date, end_date)
    daily = result.get('daily_data', {})
    
    print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"Total dates found: {len(daily)}")
    print()
    
    for date_key in sorted(daily.keys()):
        platforms = daily[date_key]
        total_imps = 0
        total_rev = 0
        for plat, ad_types in platforms.items():
            for ad_type, metrics in ad_types.items():
                total_imps += metrics.get('impressions', 0)
                total_rev += metrics.get('revenue', 0)
        print(f"{date_key}: {total_imps:,} impressions, ${total_rev:.2f}")


async def main():
    await test_dt_exchange()
    await test_meta()

if __name__ == "__main__":
    asyncio.run(main())
