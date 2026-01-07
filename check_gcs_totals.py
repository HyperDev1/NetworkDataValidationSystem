"""Check all parquet files in GCS and calculate totals."""
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
total_rows = 0

for blob in blobs:
    # Download to temp file
    with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
        tmp_path = tmp.name
    
    blob.download_to_filename(tmp_path)
    table = pq.read_table(tmp_path)
    df = table.to_pandas()
    
    max_rev = df['max_revenue'].sum()
    net_rev = df['network_revenue'].sum()
    rows = len(df)
    
    print(f'{blob.name}')
    print(f'  Rows: {rows}, MAX Rev: ${max_rev:.2f}, Net Rev: ${net_rev:.2f}')
    
    total_max_rev += max_rev
    total_net_rev += net_rev
    total_rows += rows
    
    os.remove(tmp_path)

print()
print('=' * 60)
print(f'TOTALS: {total_rows} rows, MAX: ${total_max_rev:.2f}, Network: ${total_net_rev:.2f}')
