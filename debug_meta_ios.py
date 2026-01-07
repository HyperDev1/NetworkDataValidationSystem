"""Debug script to compare Meta iOS data between MAX and Meta API."""
from datetime import datetime, timedelta, timezone
from src.config import Config
from src.fetchers import ApplovinFetcher, MetaFetcher

config = Config()

# Get MAX data for Meta iOS
print("=" * 60)
print("APPALOVIN MAX - META iOS DATA")
print("=" * 60)

applovin_config = config.get_applovin_config()
fetcher = ApplovinFetcher(
    api_key=applovin_config['api_key'],
    applications=applovin_config.get('applications', [])
)

now_utc = datetime.now(timezone.utc)
end_date = now_utc.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)

data = fetcher.fetch_data(end_date, end_date)
rows = data.get('comparison_rows', [])

# Filter Meta iOS rows
meta_ios = [r for r in rows if ('META' in r.get('network', '').upper() or 'FACEBOOK' in r.get('network', '').upper()) and 'iOS' in r.get('application', '')]

print(f"\nDate: {end_date.strftime('%Y-%m-%d')}")
print("\nMAX reports for Meta iOS:")
total_max_imps = 0
total_max_rev = 0
for r in meta_ios:
    print(f"  {r['ad_type']}: {r['max_impressions']:,} imps, ${r['max_revenue']:.2f}")
    total_max_imps += r['max_impressions']
    total_max_rev += r['max_revenue']
print(f"  TOTAL: {total_max_imps:,} imps, ${total_max_rev:.2f}")

# Get Meta API data
print("\n" + "=" * 60)
print("META API - iOS DATA (Hourly Aggregate)")
print("=" * 60)

meta_config = config.get_meta_config()
meta_fetcher = MetaFetcher(
    access_token=meta_config['access_token'],
    business_id=meta_config['business_id']
)

meta_data = meta_fetcher.fetch_hourly_aggregate(end_date)
ios_data = meta_data['platform_data']['ios']

print(f"\nMeta API reports for iOS:")
total_meta_imps = 0
total_meta_rev = 0
for ad_type, ad_data in ios_data['ad_data'].items():
    if ad_data['impressions'] > 0:
        print(f"  {ad_type}: {ad_data['impressions']:,} imps, ${ad_data['revenue']:.2f}")
        total_meta_imps += ad_data['impressions']
        total_meta_rev += ad_data['revenue']
print(f"  TOTAL: {total_meta_imps:,} imps, ${total_meta_rev:.2f}")

print("\n" + "=" * 60)
print("COMPARISON")
print("=" * 60)
print(f"\nImpressions: MAX={total_max_imps:,} vs Meta={total_meta_imps:,} (diff: {total_meta_imps - total_max_imps:+,})")
print(f"Revenue: MAX=${total_max_rev:.2f} vs Meta=${total_meta_rev:.2f} (diff: ${total_meta_rev - total_max_rev:+.2f})")
