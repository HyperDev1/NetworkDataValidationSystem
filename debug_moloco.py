"""Debug Moloco ad_unit_id mapping."""
import yaml
from src.fetchers import MolocoFetcher
from datetime import datetime

with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

moloco = config['networks']['moloco']

print("=" * 60)
print("MOLOCO AD UNIT MAPPING DEBUG")
print("=" * 60)

print(f"\nConfig ad_unit_mapping:")
for ad_unit_id, ad_type in moloco.get('ad_unit_mapping', {}).items():
    print(f"  {ad_unit_id}: {ad_type}")

fetcher = MolocoFetcher(
    email=moloco['email'],
    password=moloco['password'],
    platform_id=moloco['platform_id'],
    publisher_id=moloco['publisher_id'],
    app_bundle_ids=moloco.get('app_bundle_ids'),
    time_zone=moloco.get('time_zone', 'UTC'),
    ad_unit_mapping=moloco.get('ad_unit_mapping', {})
)

print(f"\nFetcher ad_unit_mapping:")
for ad_unit_id, ad_type in fetcher.ad_unit_mapping.items():
    print(f"  {ad_unit_id}: {ad_type}")

# Fetch data
start = datetime(2026, 1, 4)
end = datetime(2026, 1, 4)

print(f"\nFetching data for {start.strftime('%Y-%m-%d')}...")
data = fetcher.fetch_data(start, end)

print(f"\nResults:")
print(f"  Total: ${data['revenue']:.2f}")
print(f"\n  Platform breakdown:")
for platform, pdata in data['platform_data'].items():
    if pdata['impressions'] > 0:
        print(f"    {platform}:")
        for ad_type, ad_data in pdata['ad_data'].items():
            if ad_data['impressions'] > 0:
                print(f"      {ad_type}: ${ad_data['revenue']:.2f} | {ad_data['impressions']} imps")

