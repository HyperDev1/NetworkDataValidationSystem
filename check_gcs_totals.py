"""Check all parquet files in GCS and calculate totals with delta verification."""
import pyarrow.parquet as pq
from google.cloud import storage
from google.oauth2 import service_account
from src.config import Config
import tempfile
import os

config = Config()
gcp = config.get_gcp_config()

credentials = service_account.Credentials.from_service_account_file(
    gcp.get('service_account_path', 'credentials/gcp_service_account.json')
)
client = storage.Client(project=gcp['project_id'], credentials=credentials)
bucket = client.bucket(gcp['bucket_name'])

# List all files and calculate totals
blobs = list(bucket.list_blobs(prefix='network_data/dt='))
print(f'Total files in GCS: {len(blobs)}')
print()

total_max_rev = 0
total_net_rev = 0
total_max_imp = 0
total_net_imp = 0
total_rows = 0
all_mismatches = []

for blob in blobs:
    # Download to temp file
    with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
        tmp_path = tmp.name
    
    blob.download_to_filename(tmp_path)
    table = pq.read_table(tmp_path)
    df = table.to_pandas()
    
    max_rev = df['max_revenue'].sum()
    net_rev = df['network_revenue'].sum()
    max_imp = df['max_impressions'].sum()
    net_imp = df['network_impressions'].sum()
    rows = len(df)
    
    # Calculate expected deltas
    rev_delta = ((net_rev - max_rev) / max_rev * 100) if max_rev > 0 else 0
    imp_delta = ((net_imp - max_imp) / max_imp * 100) if max_imp > 0 else 0
    
    print(f'{blob.name}')
    print(f'  Rows: {rows}')
    print(f'  Revenue: MAX ${max_rev:,.2f} → Network ${net_rev:,.2f} (Delta: {rev_delta:+.1f}%)')
    print(f'  Impressions: MAX {max_imp:,} → Network {net_imp:,} (Delta: {imp_delta:+.1f}%)')
    
    # Verify stored deltas vs calculated
    mismatches = []
    for idx, row in df.iterrows():
        # Revenue delta check
        if row['max_revenue'] > 0 and row['rev_delta_pct'] is not None:
            calc = ((row['network_revenue'] - row['max_revenue']) / row['max_revenue']) * 100
            if abs(row['rev_delta_pct'] - calc) > 0.2:
                mismatches.append(('rev', row['network'], row['max_revenue'], row['network_revenue'], row['rev_delta_pct'], calc))
        
        # Impression delta check
        if row['max_impressions'] > 0 and row['imp_delta_pct'] is not None:
            calc = ((row['network_impressions'] - row['max_impressions']) / row['max_impressions']) * 100
            if abs(row['imp_delta_pct'] - calc) > 0.2:
                mismatches.append(('imp', row['network'], row['max_impressions'], row['network_impressions'], row['imp_delta_pct'], calc))
        
        # eCPM delta check
        if row['max_ecpm'] > 0 and row['ecpm_delta_pct'] is not None:
            calc = ((row['network_ecpm'] - row['max_ecpm']) / row['max_ecpm']) * 100
            if abs(row['ecpm_delta_pct'] - calc) > 0.2:
                mismatches.append(('ecpm', row['network'], row['max_ecpm'], row['network_ecpm'], row['ecpm_delta_pct'], calc))
    
    if mismatches:
        print(f'  ⚠️ Delta mismatches: {len(mismatches)}')
        all_mismatches.extend(mismatches)
    else:
        print(f'  ✅ All deltas verified')
    print()
    
    total_max_rev += max_rev
    total_net_rev += net_rev
    total_max_imp += max_imp
    total_net_imp += net_imp
    total_rows += rows
    
    os.remove(tmp_path)

print('=' * 70)
total_rev_delta = ((total_net_rev - total_max_rev) / total_max_rev * 100) if total_max_rev > 0 else 0
total_imp_delta = ((total_net_imp - total_max_imp) / total_max_imp * 100) if total_max_imp > 0 else 0

print(f'TOTALS: {total_rows} rows')
print(f'  Revenue: MAX ${total_max_rev:,.2f} → Network ${total_net_rev:,.2f} (Delta: {total_rev_delta:+.1f}%)')
print(f'  Impressions: MAX {total_max_imp:,} → Network {total_net_imp:,} (Delta: {total_imp_delta:+.1f}%)')

if all_mismatches:
    print()
    print(f'⚠️ TOTAL DELTA MISMATCHES: {len(all_mismatches)}')
    for m in all_mismatches[:10]:
        print(f'  {m[0].upper()} - {m[1]}: MAX={m[2]:.2f}, Net={m[3]:.2f}, Stored={m[4]:.1f}%, Calc={m[5]:.1f}%')
else:
    print()
    print('✅ All delta calculations verified - no mismatches found!')
