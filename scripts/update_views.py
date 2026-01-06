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
    COUNT(DISTINCT network) AS total_networks,
    COUNT(*) AS total_records,
    -- Original timestamp fields
    MAX(date) AS last_report_date,
    MIN(date) AS first_report_date,
    MAX(fetched_at) AS last_sync_time,
    -- STRING formatted for Looker scorecards (use these in Text components)
    CAST(MAX(date) AS STRING) AS last_report_date_str,
    CAST(MIN(date) AS STRING) AS first_report_date_str,
    FORMAT_TIMESTAMP('%Y-%m-%d %H:%M', MAX(fetched_at)) AS last_sync_str,
    FORMAT_TIMESTAMP('%d %b %Y %H:%M', MAX(fetched_at)) AS last_sync_display,
    CONCAT('Report: ', CAST(MAX(date) AS STRING), ' | Sync: ', FORMAT_TIMESTAMP('%H:%M', MAX(fetched_at))) AS status_line,
    -- Numeric fields
    TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(fetched_at), HOUR) AS hours_since_last_sync,
    ROUND(SUM(max_revenue), 2) AS total_max_revenue,
    ROUND(SUM(network_revenue), 2) AS total_network_revenue
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
WITH network_delays AS (
    SELECT 'Mintegral Bidding' as network, 1 as expected_delay_days UNION ALL
    SELECT 'Unity Bidding', 1 UNION ALL
    SELECT 'Admob Bidding', 2 UNION ALL
    SELECT 'Google Bidding', 2 UNION ALL
    SELECT 'Ironsource Bidding', 1 UNION ALL
    SELECT 'Meta Bidding', 3 UNION ALL
    SELECT 'Inmobi Bidding', 1 UNION ALL
    SELECT 'Moloco Bidding', 1 UNION ALL
    SELECT 'Bidmachine Bidding', 1 UNION ALL
    SELECT 'Liftoff Monetize Bidding', 1 UNION ALL
    SELECT 'Vungle Bidding', 1 UNION ALL
    SELECT 'Chartboost Bidding', 1 UNION ALL
    SELECT 'Fyber Bidding', 1 UNION ALL
    SELECT 'Tiktok Bidding', 1 UNION ALL
    SELECT 'Pangle Bidding', 1 UNION ALL
    SELECT 'Applovin Bidding', 0 UNION ALL
    SELECT 'Applovin Exchange', 0 UNION ALL
    SELECT 'Google Ad Manager', 2
),
network_stats AS (
    SELECT 
        network,
        COUNT(*) as record_count,
        MAX(date) as last_report_date,
        MAX(fetched_at) as last_sync_time,
        ROUND(SUM(max_revenue), 2) as total_max_revenue,
        ROUND(SUM(network_revenue), 2) as total_network_revenue
    FROM `gen-lang-client-0468554395.ad_network_analytics.network_comparison`
    GROUP BY network
)
SELECT 
    ns.network,
    ns.record_count,
    ns.last_report_date,
    ns.last_sync_time,
    -- STRING formatted for display
    CAST(ns.last_report_date AS STRING) AS last_report_date_str,
    FORMAT_TIMESTAMP('%Y-%m-%d %H:%M', ns.last_sync_time) AS last_sync_str,
    -- Delay info
    COALESCE(nd.expected_delay_days, 1) as expected_delay_days,
    DATE_SUB(CURRENT_DATE(), INTERVAL COALESCE(nd.expected_delay_days, 1) DAY) as expected_latest_date,
    CAST(DATE_SUB(CURRENT_DATE(), INTERVAL COALESCE(nd.expected_delay_days, 1) DAY) AS STRING) as expected_latest_date_str,
    DATE_DIFF(DATE_SUB(CURRENT_DATE(), INTERVAL COALESCE(nd.expected_delay_days, 1) DAY), ns.last_report_date, DAY) as days_behind_expected,
    -- Status text
    CASE 
        WHEN DATE_DIFF(DATE_SUB(CURRENT_DATE(), INTERVAL COALESCE(nd.expected_delay_days, 1) DAY), ns.last_report_date, DAY) <= 0 THEN 'OK'
        ELSE CONCAT(CAST(DATE_DIFF(DATE_SUB(CURRENT_DATE(), INTERVAL COALESCE(nd.expected_delay_days, 1) DAY), ns.last_report_date, DAY) AS STRING), ' days behind')
    END AS status,
    -- Revenue
    ns.total_max_revenue,
    ns.total_network_revenue,
    ROUND(SAFE_DIVIDE(ns.total_network_revenue - ns.total_max_revenue, ns.total_max_revenue) * 100, 2) as overall_rev_delta_pct
FROM network_stats ns
LEFT JOIN network_delays nd ON ns.network = nd.network
ORDER BY ns.total_max_revenue DESC
"""
client.query(sql).result()
print('network_data_availability view updated!')

# Test
print()
print('=== Testing sync_metadata ===')
result = client.query('SELECT last_report_date_str, last_sync_str, last_sync_display, status_line FROM `gen-lang-client-0468554395.ad_network_analytics.sync_metadata`').result()
for row in result:
    print(f'  last_report_date_str: {row.last_report_date_str}')
    print(f'  last_sync_str: {row.last_sync_str}')
    print(f'  last_sync_display: {row.last_sync_display}')
    print(f'  status_line: {row.status_line}')

print()
print('=== Testing network_data_availability (sample) ===')
result = client.query('SELECT network, last_report_date_str, last_sync_str, status FROM `gen-lang-client-0468554395.ad_network_analytics.network_data_availability` LIMIT 5').result()
for row in result:
    print(f'  {row.network}: Report={row.last_report_date_str}, Sync={row.last_sync_str}, Status={row.status}')

print()
print('Done! Use *_str fields in Looker Text components or Table columns.')
