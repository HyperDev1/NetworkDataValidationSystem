"""Recreate BigQuery external table with proper TIMESTAMP schema."""
import os
from google.cloud import bigquery

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'credentials/gcp_service_account.json'

client = bigquery.Client()

# Drop existing table
print('Dropping existing external table...')
client.query('DROP EXTERNAL TABLE IF EXISTS `gen-lang-client-0468554395.ad_network_analytics.network_comparison`').result()

# Recreate with proper schema
print('Creating external table with proper TIMESTAMP schema...')
sql = """
CREATE EXTERNAL TABLE `gen-lang-client-0468554395.ad_network_analytics.network_comparison` (
    date DATE,
    network STRING,
    platform STRING,
    ad_type STRING,
    application STRING,
    max_revenue FLOAT64,
    max_impressions INT64,
    max_ecpm FLOAT64,
    network_revenue FLOAT64,
    network_impressions INT64,
    network_ecpm FLOAT64,
    rev_delta_pct FLOAT64,
    imp_delta_pct FLOAT64,
    ecpm_delta_pct FLOAT64,
    fetched_at TIMESTAMP
)
WITH PARTITION COLUMNS (dt DATE)
OPTIONS (
    format = 'PARQUET',
    uris = ['gs://network_comparison_bucket/network_data/*'],
    hive_partition_uri_prefix = 'gs://network_comparison_bucket/network_data/'
)
"""
client.query(sql).result()
print('External table created!')

# Update sync_metadata view with formatted timestamp
print('Updating sync_metadata view...')
sql = """
CREATE OR REPLACE VIEW `gen-lang-client-0468554395.ad_network_analytics.sync_metadata` AS
SELECT
    MAX(fetched_at) AS last_sync_time,
    FORMAT_TIMESTAMP('%Y-%m-%d %H:%M', MAX(fetched_at)) AS last_sync_str,
    FORMAT_TIMESTAMP('%d %b %Y %H:%M', MAX(fetched_at)) AS last_sync_display
FROM `gen-lang-client-0468554395.ad_network_analytics.network_comparison`
"""
client.query(sql).result()
print('sync_metadata view updated!')

# Update network_sync_summary view
print('Updating network_sync_summary view...')
sql = """
CREATE OR REPLACE VIEW `gen-lang-client-0468554395.ad_network_analytics.network_sync_summary` AS
SELECT
    network,
    COUNT(*) AS record_count,
    MAX(date) AS last_report_date,
    MAX(fetched_at) AS last_sync_time,
    FORMAT_TIMESTAMP('%Y-%m-%d %H:%M', MAX(fetched_at)) AS last_sync_formatted,
    ROUND(SUM(max_revenue), 2) AS total_max_revenue,
    ROUND(SUM(network_revenue), 2) AS total_network_revenue,
    ROUND(SAFE_DIVIDE(
        SUM(network_revenue) - SUM(max_revenue),
        SUM(max_revenue)
    ) * 100, 2) AS overall_rev_delta_pct
FROM `gen-lang-client-0468554395.ad_network_analytics.network_comparison`
GROUP BY network
ORDER BY total_max_revenue DESC
"""
client.query(sql).result()
print('network_sync_summary view updated!')

# Test
print()
print('Testing sync_metadata:')
result = client.query('SELECT * FROM `gen-lang-client-0468554395.ad_network_analytics.sync_metadata`').result()
for row in result:
    print(f'  Last Sync: {row.last_sync_formatted}')
    print(f'  Last Report Date: {row.last_report_date}')
    print(f'  Hours Since Sync: {row.hours_since_last_sync}')
    print(f'  Total Networks: {row.total_networks}')

print()
print('Done! Now fetched_at will appear as TIMESTAMP in Looker.')
print('Use last_sync_formatted for readable date/time display.')
