"""Check for duplicate files in GCS for a specific date."""
from google.cloud import storage
from google.oauth2 import service_account
from src.config import Config

config = Config()
gcp = config.get_gcp_config()

# Use service account
credentials = service_account.Credentials.from_service_account_file(
    gcp.get('service_account_path', 'credentials/gcp_service_account.json')
)
client = storage.Client(project=gcp['project_id'], credentials=credentials)
bucket = client.bucket(gcp['bucket_name'])

print("=" * 60)
print("GCS FILES CHECK")
print("=" * 60)

# Check files for Jan 6
blobs = list(bucket.list_blobs(prefix='network_data/dt=2026-01-06'))
print(f"\nFiles for 2026-01-06: {len(blobs)}")
for b in blobs:
    print(f"  {b.name} ({b.size:,} bytes)")

# Check all dates
print("\n" + "=" * 60)
print("ALL DATES")
print("=" * 60)
all_blobs = list(bucket.list_blobs(prefix='network_data/dt='))
dates = {}
for b in all_blobs:
    # Extract date from path
    parts = b.name.split('/')
    for p in parts:
        if p.startswith('dt='):
            date = p.replace('dt=', '')
            if date not in dates:
                dates[date] = []
            dates[date].append(b.name)
            break

for date in sorted(dates.keys()):
    files = dates[date]
    print(f"\n{date}: {len(files)} file(s)")
    for f in files:
        print(f"  - {f.split('/')[-1]}")
