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
    
    -- Hourly data metadata (Meta only)
    hour_range STRING OPTIONS(description="Hour range for hourly aggregated data (Meta only, e.g., '00:00-23:00 UTC (24/24)')"),
    
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


-- Sync metadata summary view for dashboard header
CREATE OR REPLACE VIEW `gen-lang-client-0468554395.ad_network_analytics.sync_metadata` AS
SELECT
    MAX(fetched_at) AS last_sync_time,
    FORMAT_TIMESTAMP('%Y-%m-%d %H:%M', MAX(fetched_at)) AS last_sync_str,
    FORMAT_TIMESTAMP('%d %b %Y %H:%M', MAX(fetched_at)) AS last_sync_display
FROM `gen-lang-client-0468554395.ad_network_analytics.network_comparison`;


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
