-- BigQuery Table Setup for Network Data Validation System
-- Run this in BigQuery Console or via bq command-line tool
--
-- Prerequisites:
-- 1. Create a dataset first:
--    bq mk --dataset gen-lang-client-0468554395:ad_network_analytics
--
-- 2. Then run this SQL to create the table

-- Main comparison data table with partitioning and clustering
CREATE TABLE IF NOT EXISTS `gen-lang-client-0468554395.ad_network_analytics.network_comparison` (
    -- Date fields
    date DATE NOT NULL OPTIONS(description="Report date (the date the metrics are for)"),
    
    -- Dimensions
    network STRING NOT NULL OPTIONS(description="Network name (unity, ironsource, meta, etc.)"),
    platform STRING NOT NULL OPTIONS(description="Platform (android, ios)"),
    ad_type STRING NOT NULL OPTIONS(description="Ad type (banner, interstitial, rewarded)"),
    application STRING OPTIONS(description="Application name"),
    
    -- AppLovin MAX reported metrics
    max_revenue FLOAT64 OPTIONS(description="Revenue reported by AppLovin MAX (USD)"),
    max_impressions INT64 OPTIONS(description="Impressions reported by AppLovin MAX"),
    max_ecpm FLOAT64 OPTIONS(description="eCPM reported by AppLovin MAX"),
    
    -- Network's own reported metrics
    network_revenue FLOAT64 OPTIONS(description="Revenue reported by the network directly (USD)"),
    network_impressions INT64 OPTIONS(description="Impressions reported by the network directly"),
    network_ecpm FLOAT64 OPTIONS(description="eCPM reported by the network directly"),
    
    -- Delta calculations (percentage difference)
    rev_delta_pct FLOAT64 OPTIONS(description="Revenue difference percentage ((network-max)/max * 100)"),
    imp_delta_pct FLOAT64 OPTIONS(description="Impressions difference percentage"),
    ecpm_delta_pct FLOAT64 OPTIONS(description="eCPM difference percentage"),
    
    -- Metadata
    fetched_at TIMESTAMP NOT NULL OPTIONS(description="When this data was fetched and recorded")
)
PARTITION BY date
CLUSTER BY network, platform
OPTIONS(
    description="Network data comparison: AppLovin MAX vs individual network reports",
    labels=[("team", "adops"), ("data_source", "network_validation_system")],
    partition_expiration_days=NULL,  -- No expiration, keep all historical data
    require_partition_filter=FALSE   -- Set to TRUE in production for cost savings
);


-- Optional: Create a view for daily summaries with sync metadata
CREATE OR REPLACE VIEW `gen-lang-client-0468554395.ad_network_analytics.daily_summary` AS
SELECT
    date,
    network,
    platform,
    
    -- Totals
    SUM(max_revenue) AS total_max_revenue,
    SUM(network_revenue) AS total_network_revenue,
    SUM(max_impressions) AS total_max_impressions,
    SUM(network_impressions) AS total_network_impressions,
    
    -- Weighted average eCPM
    SAFE_DIVIDE(SUM(max_revenue) * 1000, SUM(max_impressions)) AS avg_max_ecpm,
    SAFE_DIVIDE(SUM(network_revenue) * 1000, SUM(network_impressions)) AS avg_network_ecpm,
    
    -- Overall delta
    SAFE_DIVIDE(
        SUM(network_revenue) - SUM(max_revenue),
        SUM(max_revenue)
    ) * 100 AS overall_rev_delta_pct,
    
    -- Record count
    COUNT(*) AS record_count,
    
    -- Sync metadata
    MAX(fetched_at) AS last_sync_time,
    MAX(date) AS last_report_date
    
FROM `gen-lang-client-0468554395.ad_network_analytics.network_comparison`
GROUP BY date, network, platform
ORDER BY date DESC, network, platform;


-- Sync metadata summary view for dashboard header
CREATE OR REPLACE VIEW `gen-lang-client-0468554395.ad_network_analytics.sync_metadata` AS
SELECT
    COUNT(DISTINCT network) AS total_networks,
    COUNT(*) AS total_records,
    MAX(date) AS last_report_date,
    MIN(date) AS first_report_date,
    MAX(fetched_at) AS last_sync_time,
    TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(fetched_at), HOUR) AS hours_since_last_sync,
    SUM(max_revenue) AS total_max_revenue,
    SUM(network_revenue) AS total_network_revenue
FROM `gen-lang-client-0468554395.ad_network_analytics.network_comparison`;


-- Network-level sync summary
CREATE OR REPLACE VIEW `gen-lang-client-0468554395.ad_network_analytics.network_sync_summary` AS
SELECT
    network,
    COUNT(*) AS record_count,
    MAX(date) AS last_report_date,
    MAX(fetched_at) AS last_sync_time,
    SUM(max_revenue) AS total_max_revenue,
    SUM(network_revenue) AS total_network_revenue,
    SAFE_DIVIDE(
        SUM(network_revenue) - SUM(max_revenue),
        SUM(max_revenue)
    ) * 100 AS overall_rev_delta_pct
FROM `gen-lang-client-0468554395.ad_network_analytics.network_comparison`
GROUP BY network
ORDER BY total_max_revenue DESC;


-- Optional: Create a view for discrepancy alerts (>5% difference)
CREATE OR REPLACE VIEW `gen-lang-client-0468554395.ad_network_analytics.discrepancy_alerts` AS
SELECT
    date,
    network,
    platform,
    ad_type,
    application,
    max_revenue,
    network_revenue,
    rev_delta_pct,
    max_impressions,
    network_impressions,
    imp_delta_pct,
    fetched_at
FROM `gen-lang-client-0468554395.ad_network_analytics.network_comparison`
WHERE 
    ABS(rev_delta_pct) > 5 
    OR ABS(imp_delta_pct) > 5
ORDER BY date DESC, ABS(rev_delta_pct) DESC;


-- Optional: Create External Table linked to GCS (alternative to loading data)
-- This queries data directly from GCS without copying to BigQuery
-- Useful for cost optimization with infrequent queries
/*
CREATE OR REPLACE EXTERNAL TABLE `gen-lang-client-0468554395.ad_network_analytics.network_comparison_external`
WITH PARTITION COLUMNS (
    dt DATE  -- Hive partition column
)
OPTIONS (
    format = 'PARQUET',
    uris = ['gs://network_comparison_bucket/network_data/*'],
    hive_partition_uri_prefix = 'gs://network_comparison_bucket/network_data/',
    require_hive_partition_filter = false
);
*/


-- Sample queries for verification:

-- 1. Check data was loaded correctly
-- SELECT date, network, COUNT(*) as rows 
-- FROM `your-project-id.ad_network_analytics.network_comparison`
-- GROUP BY date, network
-- ORDER BY date DESC
-- LIMIT 20;

-- 2. Daily revenue by network
-- SELECT 
--     date,
--     network,
--     SUM(max_revenue) as max_rev,
--     SUM(network_revenue) as net_rev,
--     ROUND((SUM(network_revenue) - SUM(max_revenue)) / SUM(max_revenue) * 100, 2) as delta_pct
-- FROM `your-project-id.ad_network_analytics.network_comparison`
-- WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
-- GROUP BY date, network
-- ORDER BY date DESC, network;

-- 3. Find largest discrepancies
-- SELECT * FROM `your-project-id.ad_network_analytics.discrepancy_alerts`
-- WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
-- ORDER BY ABS(rev_delta_pct) DESC
-- LIMIT 20;
