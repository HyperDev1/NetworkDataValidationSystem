"""Update BigQuery views with STRING formatted fields for Looker scorecards."""
import os
from google.cloud import bigquery

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'credentials/gcp_service_account.json'

client = bigquery.Client()

# Update sync_metadata view with STRING formatted fields for Looker metrics
print('Updating sync_metadata view with STRING fields...')
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
    -- STRING formatted for display
    CAST(MAX(date) AS STRING) AS last_report_date_str,
    FORMAT_TIMESTAMP('%Y-%m-%d %H:%M', MAX(fetched_at)) AS last_sync_str,
    -- Numeric fields
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

# Update network_data_availability view
print('Updating network_data_availability view...')
sql = """
CREATE OR REPLACE VIEW `gen-lang-client-0468554395.ad_network_analytics.network_data_availability` AS
SELECT 
    network,
    COUNT(*) as record_count,
    MAX(date) as last_report_date,
    MAX(fetched_at) as last_sync_time,
    -- STRING formatted for display
    CAST(MAX(date) AS STRING) AS last_report_date_str,
    FORMAT_TIMESTAMP('%Y-%m-%d %H:%M', MAX(fetched_at)) AS last_sync_str
FROM `gen-lang-client-0468554395.ad_network_analytics.network_comparison`
GROUP BY network
ORDER BY last_report_date DESC
"""
client.query(sql).result()
print('network_data_availability view updated!')

# Test
print()
print('=== Testing sync_metadata ===')
result = client.query('SELECT last_sync_str, last_sync_display FROM `gen-lang-client-0468554395.ad_network_analytics.sync_metadata`').result()
for row in result:
    print(f'  last_sync_str: {row.last_sync_str}')
    print(f'  last_sync_display: {row.last_sync_display}')

print()
print('=== Testing network_data_availability (sample) ===')
result = client.query('SELECT network, record_count, last_report_date_str, last_sync_str FROM `gen-lang-client-0468554395.ad_network_analytics.network_data_availability` LIMIT 5').result()
for row in result:
    print(f'  {row.network}: Records={row.record_count}, Report={row.last_report_date_str}, Sync={row.last_sync_str}')

print()
print('Done! Use *_str fields in Looker Text components or Table columns.')
