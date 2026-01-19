"""
Network Data Validation System - Main Entry Point

Workflow:
1. Fetch AppLovin MAX data (network/day breakdown) for date range
2. Fetch Network API data, determine last_available_date per network
3. Export all data to GCS (Looker)
4. Compare MAX vs Network at each network's last_available_date
5. Send Slack alert (threshold exceeded) or success message

CLI Arguments:
    --start_date YYYY-MM-DD : Start date (default: end_date - 7)
    --end_date YYYY-MM-DD   : End date (default: UTC now - 1)
    --no_slack_message      : Skip Slack notification
    --no_gcs_export         : Skip GCS export
    --schedule              : Run as scheduled service (continuous loop)
"""
import sys
import io
import asyncio
import logging
import argparse
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple, Set

from src.config import Config
from src.fetchers import ApplovinFetcher, FetcherFactory
from src.notifiers import SlackNotifier
from src.exporters import GCSExporter
from src.enums import NetworkName

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Fix console encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


# =============================================================================
# Network Display Name Mapping
# =============================================================================

NETWORK_DISPLAY_NAME_MAP = {
    'Vungle Bidding': 'Liftoff Bidding',
    'Vungle': 'Liftoff Bidding',
    'VUNGLE_BIDDING': 'Liftoff Bidding',
    'VUNGLE': 'Liftoff Bidding',
    'Liftoff Monetize Bidding': 'Liftoff Bidding',
    'Fyber Bidding': 'DT Exchange Bidding',
    'Fyber': 'DT Exchange Bidding',
    'FYBER_BIDDING': 'DT Exchange Bidding',
    'FYBER': 'DT Exchange Bidding',
    'Tiktok Bidding': 'Pangle Bidding',
    'Tiktok': 'Pangle Bidding',
    'TIKTOK_BIDDING': 'Pangle Bidding',
    'TIKTOK': 'Pangle Bidding',
    'TikTok Bidding': 'Pangle Bidding',
    'TikTok': 'Pangle Bidding',
    'Facebook Network': 'Meta Bidding',
    'Facebook Bidding': 'Meta Bidding',
    'FACEBOOK': 'Meta Bidding',
    'FACEBOOK_BIDDING': 'Meta Bidding',
    'ironSource Bidding': 'Ironsource Bidding',
    'ironSource': 'Ironsource Bidding',
    'IronSource Bidding': 'Ironsource Bidding',
    'IronSource': 'Ironsource Bidding',
    'InMobi Bidding': 'Inmobi Bidding',
    'InMobi': 'Inmobi Bidding',
    'BidMachine Bidding': 'Bidmachine Bidding',
    'BidMachine': 'Bidmachine Bidding',
    'Hyprmx Network': 'HyprMX',
    'HYPRMX_NETWORK': 'HyprMX',
}


def _get_network_key(network_name: str) -> Optional[str]:
    """Convert AppLovin network name to internal fetcher key using NetworkName enum."""
    try:
        network_enum = NetworkName.from_api_name(network_name)
        if network_enum is None:
            return None
        return network_enum.value
    except (ValueError, AttributeError):
        return None


def _calculate_delta(max_val: float, network_val: float) -> str:
    """Calculate delta percentage."""
    if max_val == 0 and network_val == 0:
        return "0.0%"
    elif max_val == 0:
        return "+∞%"
    
    delta = ((network_val - max_val) / max_val) * 100
    sign = "+" if delta > 0 else ""
    return f"{sign}{delta:.1f}%"


def _get_last_available_date(daily_data: Dict[str, Any]) -> Optional[str]:
    """
    Find the last date with valid data (impressions > 0) from daily_data.
    
    Args:
        daily_data: Dictionary with date keys containing platform/ad_type data
        
    Returns:
        Last date string (YYYY-MM-DD) with valid data, or None if no data
    """
    if not daily_data:
        return None
    
    valid_dates = []
    for date_str, date_data in daily_data.items():
        # Check if any platform/ad_type has impressions > 0
        has_data = False
        for platform_data in date_data.values():
            if isinstance(platform_data, dict):
                for ad_data in platform_data.values():
                    if isinstance(ad_data, dict) and ad_data.get('impressions', 0) > 0:
                        has_data = True
                        break
            if has_data:
                break
        if has_data:
            valid_dates.append(date_str)
    
    if not valid_dates:
        return None
    
    # Return the latest valid date
    return sorted(valid_dates)[-1]


def _create_comparison_rows(
    max_rows: List[Dict],
    network_data: Dict[str, Any],
    target_date: str,
    network_key: str
) -> List[Dict]:
    """
    Create comparison rows for a specific network and date.
    
    Args:
        max_rows: All MAX rows
        network_data: Network API data with daily_data
        target_date: The date to compare (network's last_available_date)
        network_key: The network key (e.g., 'meta', 'unity')
        
    Returns:
        List of comparison row dictionaries
    """
    comparison_rows = []
    net_daily_data = network_data.get('daily_data', {})
    
    for row in max_rows:
        row_date = row.get('date', '')
        if row_date != target_date:
            continue
        
        network_name = row.get('network', '')
        row_network_key = _get_network_key(network_name)
        
        if row_network_key != network_key:
            continue
        
        platform = 'ios' if 'iOS' in row.get('application', '') else 'android'
        ad_type = row.get('ad_type', '').lower()
        
        # Get network data for this row
        net_revenue = None
        net_impressions = None
        net_ecpm = None
        has_network_data = False
        
        if target_date in net_daily_data:
            date_data = net_daily_data[target_date]
            platform_data = date_data.get(platform, {})
            ad_data = platform_data.get(ad_type, {})
            
            if ad_data.get('impressions', 0) > 0:
                net_revenue = ad_data.get('revenue', 0)
                net_impressions = ad_data.get('impressions', 0)
                net_ecpm = (net_revenue / net_impressions * 1000) if net_impressions > 0 else 0
                has_network_data = True
        
        # Calculate deltas
        if has_network_data:
            imp_delta = _calculate_delta(row['max_impressions'], net_impressions)
            rev_delta = _calculate_delta(row['max_revenue'], net_revenue)
            cpm_delta = _calculate_delta(row['max_ecpm'], net_ecpm)
        else:
            imp_delta = "N/A"
            rev_delta = "N/A"
            cpm_delta = "N/A"
        
        display_network = NETWORK_DISPLAY_NAME_MAP.get(network_name, network_name)
        
        comparison_rows.append({
            'date': target_date,
            'application': row['application'],
            'network': display_network,
            'network_key': network_key,
            'ad_type': row['ad_type'],
            'max_impressions': row['max_impressions'],
            'network_impressions': net_impressions,
            'imp_delta': imp_delta,
            'max_revenue': row['max_revenue'],
            'network_revenue': net_revenue,
            'rev_delta': rev_delta,
            'max_ecpm': row['max_ecpm'],
            'network_ecpm': net_ecpm,
            'cpm_delta': cpm_delta,
            'has_network_data': has_network_data,
        })
    
    return comparison_rows


def _create_all_comparison_rows(
    max_rows: List[Dict],
    network_data: Dict[str, Any],
    failed_networks: Set[str]
) -> List[Dict]:
    """
    Create comparison rows from all MAX data merged with available network data.
    Used for GCS export (all dates, all networks).
    """
    comparison_rows = []
    
    for row in max_rows:
        network_name = row.get('network', '')
        network_key = _get_network_key(network_name)
        
        platform = 'ios' if 'iOS' in row.get('application', '') else 'android'
        ad_type = row.get('ad_type', '').lower()
        row_date = row.get('date')
        
        display_network = NETWORK_DISPLAY_NAME_MAP.get(network_name, network_name)
        
        net_revenue = None
        net_impressions = None
        net_ecpm = None
        has_network_data = False
        
        is_applovin_network = 'applovin' in network_name.lower()
        
        if is_applovin_network:
            net_revenue = row.get('max_revenue', 0)
            net_impressions = row.get('max_impressions', 0)
            net_ecpm = row.get('max_ecpm', 0)
            has_network_data = True
        elif network_key and network_key in network_data:
            net_data = network_data[network_key]
            daily_data = net_data.get('daily_data', {})
            
            if row_date and daily_data and row_date in daily_data:
                date_data = daily_data[row_date]
                platform_data = date_data.get(platform, {})
                ad_data = platform_data.get(ad_type, {})
                
                if ad_data.get('impressions', 0) > 0:
                    net_revenue = ad_data.get('revenue', 0)
                    net_impressions = ad_data.get('impressions', 0)
                    net_ecpm = (net_revenue / net_impressions * 1000) if net_impressions > 0 else 0
                    has_network_data = True
        
        if has_network_data and net_impressions is not None:
            imp_delta = _calculate_delta(row['max_impressions'], net_impressions)
            rev_delta = _calculate_delta(row['max_revenue'], net_revenue)
            cpm_delta = _calculate_delta(row['max_ecpm'], net_ecpm)
        else:
            imp_delta = "N/A"
            rev_delta = "N/A"
            cpm_delta = "N/A"
        
        comparison_rows.append({
            'date': row_date,
            'application': row['application'],
            'network': display_network,
            'ad_type': row['ad_type'],
            'max_impressions': row['max_impressions'],
            'network_impressions': net_impressions,
            'imp_delta': imp_delta,
            'max_revenue': row['max_revenue'],
            'network_revenue': net_revenue,
            'rev_delta': rev_delta,
            'max_ecpm': row['max_ecpm'],
            'network_ecpm': net_ecpm,
            'cpm_delta': cpm_delta,
            'has_network_data': has_network_data,
        })
    
    comparison_rows.sort(key=lambda x: (x.get('date', ''), x['network'], x['application']))
    return comparison_rows


async def run_validation(
    config: Config,
    start_date: datetime,
    end_date: datetime,
    no_slack: bool = False,
    no_gcs: bool = False
) -> Dict[str, Any]:
    """
    Main validation workflow.
    
    1. Fetch AppLovin MAX data (7 days, network/day breakdown)
    2. Fetch each network API data, determine last_available_date
    3. Export all data to GCS (for Looker)
    4. Compare MAX vs Network at last_available_date for Slack report
    
    Args:
        config: Config instance
        start_date: Start date for data fetch
        end_date: End date for data fetch
        no_slack: Skip Slack notification
        no_gcs: Skip GCS export
        
    Returns:
        Result dictionary with success status and data
    """
    print(f"\n{'=' * 70}")
    print(f"📊 NETWORK DATA VALIDATION SYSTEM")
    print(f"{'=' * 70}")
    print(f"📅 Date Range: {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}")
    print(f"🔕 Slack: {'Disabled' if no_slack else 'Enabled'}")
    print(f"☁️  GCS Export: {'Disabled' if no_gcs else 'Enabled'}")
    print(f"{'=' * 70}")
    
    # Initialize AppLovin fetcher
    applovin_config = config.get_applovin_config()
    if not applovin_config or not applovin_config.get('api_key'):
        print("❌ AppLovin fetcher not configured")
        return {'success': False, 'error': 'AppLovin fetcher not configured'}
    
    applovin_fetcher = ApplovinFetcher(
        api_key=applovin_config['api_key'],
        applications=applovin_config.get('applications', [])
    )
    
    networks_config = config.get_networks_config()
    
    # Step 1: Fetch AppLovin MAX data
    print(f"\n📥 Step 1: Fetching AppLovin MAX data...")
    try:
        max_data = await applovin_fetcher.fetch_data(start_date, end_date)
        max_rows = max_data.get('comparison_rows', [])
        print(f"   ✅ Retrieved {len(max_rows)} rows from MAX")
    except Exception as e:
        logger.error(f"Failed to fetch MAX data: {e}")
        print(f"   ❌ Failed to fetch MAX data: {e}")
        return {'success': False, 'error': f'Failed to fetch MAX data: {str(e)}'}
    finally:
        if hasattr(applovin_fetcher, 'close'):
            try:
                await applovin_fetcher.close()
            except Exception:
                pass
    
    if not max_rows:
        print("   ⚠️ No MAX data available")
        return {'success': True, 'comparison_rows': [], 'message': 'No MAX data available'}
    
    # Extract networks from MAX data
    networks_in_max = set()
    for row in max_rows:
        network_key = _get_network_key(row.get('network', ''))
        if network_key:
            networks_in_max.add(network_key)
    
    # Step 2: Fetch network API data
    print(f"\n📥 Step 2: Fetching network API data...")
    networks_to_fetch = []
    for network_key in networks_in_max:
        network_config = networks_config.get(network_key, {})
        if network_config.get('enabled', False):
            networks_to_fetch.append(network_key)
    
    print(f"   Networks to fetch: {', '.join(networks_to_fetch)}")
    
    network_data: Dict[str, Any] = {}
    failed_networks: Set[str] = set()
    last_available_dates: Dict[str, str] = {}
    
    async def fetch_single_network(network_key: str) -> Tuple[str, Optional[Dict], Optional[str]]:
        """Fetch data for a single network and determine last_available_date."""
        network_config = networks_config.get(network_key, {})
        fetcher = FetcherFactory.create_fetcher(network_key, network_config)
        
        if not fetcher:
            return (network_key, None, None)
        
        try:
            data = await fetcher.fetch_data(start_date, end_date)
            daily_data = data.get('daily_data', {})
            
            # Find last_available_date (last date with valid data)
            last_date = _get_last_available_date(daily_data)
            
            if last_date:
                days_with_data = len([d for d, v in daily_data.items() 
                                      if any(p.get(a, {}).get('impressions', 0) > 0 
                                            for p in v.values() if isinstance(p, dict)
                                            for a in p.keys() if isinstance(p.get(a), dict))])
                print(f"   ✅ {network_key}: ${data.get('revenue', 0):.2f} revenue, {data.get('impressions', 0):,} impressions")
                print(f"      📅 last_available_date: {last_date} ({days_with_data} days with data)")
            else:
                print(f"   ⚠️ {network_key}: No valid data in date range")
            
            return (network_key, data, last_date)
        except Exception as e:
            logger.error(f"Error fetching {network_key}: {e}")
            print(f"   ❌ {network_key}: {str(e)}")
            return (network_key, None, None)
        finally:
            if hasattr(fetcher, 'close'):
                try:
                    await fetcher.close()
                except Exception:
                    pass
    
    if networks_to_fetch:
        tasks = [fetch_single_network(net) for net in networks_to_fetch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Unexpected error: {result}")
                continue
            network_key, data, last_date = result
            if data is not None:
                network_data[network_key] = data
                if last_date:
                    last_available_dates[network_key] = last_date
            else:
                failed_networks.add(network_key)
    
    # Step 3: Create all comparison rows (for GCS export)
    print(f"\n📊 Step 3: Creating comparison data...")
    all_comparison_rows = _create_all_comparison_rows(max_rows, network_data, failed_networks)
    print(f"   ✅ Total comparison rows: {len(all_comparison_rows)}")
    
    # Step 4: Export to GCS (all dates, all data)
    if not no_gcs:
        gcp_config = config.get_gcp_config()
        if gcp_config and gcp_config.get('enabled') and all_comparison_rows:
            print(f"\n☁️  Step 4: Exporting to GCS...")
            try:
                exporter = GCSExporter(
                    project_id=gcp_config['project_id'],
                    bucket_name=gcp_config['bucket_name'],
                    service_account_path=gcp_config.get('service_account_path'),
                    base_path=gcp_config.get('base_path', 'network_data')
                )
                
                gcs_files = exporter.export_multi_day(all_comparison_rows)
                
                if gcs_files:
                    print(f"   ✅ Exported {len(all_comparison_rows)} rows to GCS ({len(gcs_files)} files)")
                    for f in gcs_files:
                        print(f"      📁 {f}")
                else:
                    print("   ⚠️ No data exported to GCS")
            except Exception as e:
                logger.error(f"GCS export failed: {e}")
                print(f"   ❌ GCS export failed: {e}")
        else:
            print(f"\n☁️  Step 4: GCS export skipped (not configured)")
    else:
        print(f"\n☁️  Step 4: GCS export skipped (--no_gcs_export)")
    
    # Step 5: Create Slack comparison (only last_available_date per network)
    print(f"\n📤 Step 5: Preparing Slack report...")
    slack_comparison_rows = []
    
    for network_key, last_date in last_available_dates.items():
        if network_key in network_data:
            rows = _create_comparison_rows(
                max_rows, 
                network_data[network_key], 
                last_date, 
                network_key
            )
            slack_comparison_rows.extend(rows)
            print(f"   📅 {network_key}: comparing at {last_date} ({len(rows)} rows)")
    
    # Add Applovin networks (no API needed, MAX is the source)
    applovin_rows = []
    latest_date = end_date.strftime('%Y-%m-%d')
    for row in max_rows:
        network_name = row.get('network', '')
        if 'applovin' in network_name.lower() and row.get('date') == latest_date:
            display_network = NETWORK_DISPLAY_NAME_MAP.get(network_name, network_name)
            applovin_rows.append({
                'date': row.get('date'),
                'application': row['application'],
                'network': display_network,
                'network_key': 'applovin',
                'ad_type': row['ad_type'],
                'max_impressions': row['max_impressions'],
                'network_impressions': row['max_impressions'],
                'imp_delta': '0.0%',
                'max_revenue': row['max_revenue'],
                'network_revenue': row['max_revenue'],
                'rev_delta': '0.0%',
                'max_ecpm': row['max_ecpm'],
                'network_ecpm': row['max_ecpm'],
                'cpm_delta': '0.0%',
                'has_network_data': True,
            })
    
    slack_comparison_rows.extend(applovin_rows)
    slack_comparison_rows.sort(key=lambda x: (x.get('date', ''), x['network'], x['application']))
    
    print(f"   ✅ Slack report rows: {len(slack_comparison_rows)}")
    
    # Send Slack notification
    if not no_slack:
        slack_config = config.get_slack_config()
        if slack_config and slack_config.get('webhook_url') and slack_comparison_rows:
            print(f"\n📤 Step 6: Sending Slack notification...")
            
            notifier = SlackNotifier(
                webhook_url=slack_config['webhook_url'],
                channel=slack_config.get('channel'),
                looker_url=slack_config.get('looker_url')
            )
            
            threshold = config.get_slack_revenue_delta_threshold()
            min_revenue = config.get_slack_min_revenue_for_alerts()
            
            # Build network_summary: per-network totals at their last_available_date
            network_summary = {}
            for network_key, last_date in last_available_dates.items():
                # Get rows for this network at its last_available_date
                network_rows = [
                    r for r in slack_comparison_rows 
                    if r.get('network_key') == network_key and r.get('date') == last_date
                ]
                if network_rows:
                    max_rev = sum(r.get('max_revenue', 0) for r in network_rows)
                    net_rev = sum(r.get('network_revenue', 0) or 0 for r in network_rows)
                    max_imps = sum(r.get('max_impressions', 0) for r in network_rows)
                    net_imps = sum(r.get('network_impressions', 0) or 0 for r in network_rows)
                    
                    rev_delta = ((net_rev - max_rev) / max_rev * 100) if max_rev > 0 else 0
                    imp_delta = ((net_imps - max_imps) / max_imps * 100) if max_imps > 0 else 0
                    
                    # Build placement breakdown for detailed view
                    placement_breakdown = []
                    for row in network_rows:
                        if row.get('has_network_data'):
                            max_ecpm = row.get('max_ecpm', 0) or 0
                            net_ecpm = row.get('network_ecpm', 0) or 0
                            ecpm_delta = ((net_ecpm - max_ecpm) / max_ecpm * 100) if max_ecpm > 0 else 0
                            
                            # Parse delta values safely (handle ∞, N/A, etc.)
                            def parse_delta(val):
                                if val is None:
                                    return 0.0
                                if isinstance(val, (int, float)):
                                    return float(val)
                                if isinstance(val, str):
                                    val = val.replace('%', '').replace('+', '').strip()
                                    if val in ('∞', 'N/A', '-∞', 'inf', '-inf', ''):
                                        return 0.0
                                    try:
                                        return float(val)
                                    except ValueError:
                                        return 0.0
                                return 0.0
                            
                            placement_breakdown.append({
                                'application': row.get('application', ''),
                                'ad_type': row.get('ad_type', ''),
                                'max_impressions': row.get('max_impressions', 0),
                                'network_impressions': row.get('network_impressions', 0) or 0,
                                'imp_delta': parse_delta(row.get('imp_delta')),
                                'max_revenue': row.get('max_revenue', 0),
                                'network_revenue': row.get('network_revenue', 0) or 0,
                                'rev_delta': parse_delta(row.get('rev_delta')),
                                'max_ecpm': max_ecpm,
                                'network_ecpm': net_ecpm,
                                'ecpm_delta': ecpm_delta,
                            })
                    
                    # Sort by application then ad_type
                    placement_breakdown.sort(key=lambda x: (x['application'], x['ad_type']))
                    
                    network_summary[network_key] = {
                        'last_available_date': last_date,
                        'max_revenue': max_rev,
                        'network_revenue': net_rev,
                        'max_impressions': max_imps,
                        'network_impressions': net_imps,
                        'rev_delta': rev_delta,
                        'imp_delta': imp_delta,
                        'row_count': len(network_rows),
                        'threshold_exceeded': abs(rev_delta) > threshold,
                        'placement_breakdown': placement_breakdown,
                    }
            
            # Add Applovin summary (always matches since MAX is source)
            applovin_total = sum(r.get('max_revenue', 0) for r in applovin_rows)
            applovin_imps = sum(r.get('max_impressions', 0) for r in applovin_rows)
            if applovin_total > 0:
                network_summary['applovin'] = {
                    'last_available_date': latest_date,
                    'max_revenue': applovin_total,
                    'network_revenue': applovin_total,  # Same as MAX
                    'max_impressions': applovin_imps,
                    'network_impressions': applovin_imps,
                    'rev_delta': 0.0,
                    'imp_delta': 0.0,
                    'row_count': len(applovin_rows),
                    'threshold_exceeded': False,
                }
            
            # Build end_date_summary: totals for end_date (now-1)
            end_date_str = end_date.strftime('%Y-%m-%d')
            end_date_max_rows = [r for r in max_rows if r.get('date') == end_date_str]
            end_date_max_total = sum(r.get('max_revenue', 0) for r in end_date_max_rows)
            end_date_max_imps = sum(r.get('max_impressions', 0) for r in end_date_max_rows)
            
            # Network total for end_date = sum of networks that have data on end_date
            end_date_network_total = 0
            end_date_network_imps = 0
            networks_with_end_date_data = []
            for network_key, summary in network_summary.items():
                if summary['last_available_date'] == end_date_str:
                    end_date_network_total += summary['network_revenue']
                    end_date_network_imps += summary['network_impressions']
                    networks_with_end_date_data.append(network_key)
            
            end_date_summary = {
                'date': end_date_str,
                'max_revenue': end_date_max_total,
                'max_impressions': end_date_max_imps,
                'network_revenue': end_date_network_total,
                'network_impressions': end_date_network_imps,
                'networks_with_data': networks_with_end_date_data,
            }
            
            # Legacy totals for backward compatibility (sum of all network_summary)
            totals = {
                'max_revenue': sum(s['max_revenue'] for s in network_summary.values()),
                'network_revenue': sum(s['network_revenue'] for s in network_summary.values()),
                'max_impressions': sum(s['max_impressions'] for s in network_summary.values()),
                'network_impressions': sum(s['network_impressions'] for s in network_summary.values()),
            }
            
            # Include failed networks and last_available_dates in network_data for Slack
            network_data_for_slack = dict(network_data)
            if failed_networks:
                network_data_for_slack['_failed_networks'] = list(failed_networks)
            network_data_for_slack['_last_available_dates'] = last_available_dates
            network_data_for_slack['_network_summary'] = network_summary
            network_data_for_slack['_end_date_summary'] = end_date_summary
            
            # Determine report date (use end_date since that's what we're comparing against)
            report_date = end_date
            
            def network_key_resolver(network_name: str):
                try:
                    network_enum = NetworkName.from_api_name(network_name)
                    return network_enum.value if network_enum else None
                except (ValueError, AttributeError):
                    return None
            
            success = notifier.send_comparison_report(
                comparison_rows=slack_comparison_rows,
                totals=totals,
                end_date=report_date,
                network_data=network_data_for_slack,
                threshold=threshold,
                min_revenue=min_revenue,
                network_key_resolver=network_key_resolver
            )
            
            if success:
                print(f"   ✅ Slack notification sent successfully")
            else:
                print(f"   ❌ Failed to send Slack notification")
        else:
            print(f"\n📤 Step 6: Slack notification skipped (not configured or no data)")
    else:
        print(f"\n📤 Step 6: Slack notification skipped (--no_slack_message)")
    
    # Summary
    print(f"\n{'=' * 70}")
    print(f"✅ VALIDATION COMPLETE")
    print(f"{'=' * 70}")
    print(f"   📊 MAX rows: {len(max_rows)}")
    print(f"   📊 Comparison rows (GCS): {len(all_comparison_rows)}")
    print(f"   📊 Comparison rows (Slack): {len(slack_comparison_rows)}")
    print(f"   ✅ Networks fetched: {len(network_data)}")
    if failed_networks:
        print(f"   ❌ Networks failed: {', '.join(failed_networks)}")
    if last_available_dates:
        print(f"   📅 Last available dates:")
        for net, date in sorted(last_available_dates.items()):
            print(f"      - {net}: {date}")
    print(f"{'=' * 70}\n")
    
    return {
        'success': True,
        'max_rows': len(max_rows),
        'all_comparison_rows': all_comparison_rows,
        'slack_comparison_rows': slack_comparison_rows,
        'network_data': network_data,
        'failed_networks': list(failed_networks),
        'last_available_dates': last_available_dates,
    }


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Network Data Validation System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                              # Run with defaults (last 7 days)
  python main.py --end_date 2026-01-18        # End at specific date
  python main.py --start_date 2026-01-01 --end_date 2026-01-17  # Custom range
  python main.py --no_slack_message           # Skip Slack notification
  python main.py --no_gcs_export              # Skip GCS export
"""
    )
    
    parser.add_argument(
        '--start_date',
        type=str,
        help='Start date (YYYY-MM-DD). Default: end_date - 7 days'
    )
    
    parser.add_argument(
        '--end_date',
        type=str,
        help='End date (YYYY-MM-DD). Default: UTC now - 1 day'
    )
    
    parser.add_argument(
        '--no_slack_message',
        action='store_true',
        help='Skip Slack notification'
    )
    
    parser.add_argument(
        '--no_gcs_export',
        action='store_true',
        help='Skip GCS export'
    )
    
    parser.add_argument(
        '--schedule',
        action='store_true',
        help='Run as scheduled service (continuous loop)'
    )
    
    return parser.parse_args()


def run_single_validation(config: Config, args) -> bool:
    """Run a single validation cycle."""
    # Calculate date range
    now_utc = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    # End date: default to yesterday (UTC now - 1)
    if args.end_date:
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    else:
        end_date = now_utc - timedelta(days=1)
    
    # Start date: default to end_date - 7 days
    if args.start_date:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    else:
        start_date = end_date - timedelta(days=7)
    
    # Validate dates
    if start_date > end_date:
        print(f"❌ start_date ({start_date.strftime('%Y-%m-%d')}) cannot be after end_date ({end_date.strftime('%Y-%m-%d')})")
        return False
    
    print(f"📅 Date range: {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}")
    
    # Run validation
    result = asyncio.run(run_validation(
        config=config,
        start_date=start_date,
        end_date=end_date,
        no_slack=args.no_slack_message,
        no_gcs=args.no_gcs_export
    ))
    
    return result.get('success', False)


def run_scheduled(config: Config, args):
    """
    Run validation on a schedule (continuous loop).
    Checks scheduled times from config and runs validation when time matches.
    """
    import time as time_module
    
    scheduled_times = config.get_scheduled_times()
    interval_hours = config.get_scheduling_interval_hours()
    
    print(f"\n🕐 Scheduled mode started")
    print(f"📅 Running every {interval_hours} hours at: {', '.join(scheduled_times)}")
    print(f"Press Ctrl+C to stop\n")
    
    last_run_time = None
    
    while True:
        try:
            now = datetime.now()
            current_time = now.strftime('%H:%M')
            
            # Check if current time matches a scheduled time (within 1 minute window)
            should_run = False
            for scheduled_time in scheduled_times:
                if current_time == scheduled_time:
                    # Avoid running multiple times in the same minute
                    run_key = f"{now.strftime('%Y-%m-%d')}_{scheduled_time}"
                    if last_run_time != run_key:
                        should_run = True
                        last_run_time = run_key
                    break
            
            if should_run:
                print(f"\n{'='*70}")
                print(f"⏰ Scheduled run at {now.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'='*70}")
                
                try:
                    # Reload config in case it changed
                    config = Config()
                    success = run_single_validation(config, args)
                    
                    if success:
                        print(f"\n✅ Validation completed at {datetime.now().strftime('%H:%M:%S')}")
                    else:
                        print(f"\n❌ Validation failed at {datetime.now().strftime('%H:%M:%S')}")
                        
                except Exception as e:
                    print(f"\n❌ Error during validation: {str(e)}")
                    logger.exception("Scheduled validation error")
                
                print(f"\n💤 Waiting for next scheduled time...")
            
            # Sleep for 30 seconds before checking again
            time_module.sleep(30)
            
        except KeyboardInterrupt:
            print(f"\n\n🛑 Scheduled service stopped by user")
            break
        except Exception as e:
            print(f"\n❌ Scheduler error: {str(e)}")
            logger.exception("Scheduler error")
            time_module.sleep(60)  # Wait a bit before retrying


def main():
    """Main entry point."""
    print("Network Data Validation System")
    print("=" * 70)
    
    # Parse arguments
    args = parse_args()
    
    # Load configuration
    try:
        config = Config()
        print("✅ Configuration loaded successfully")
    except FileNotFoundError as e:
        print(f"❌ {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to load configuration: {str(e)}")
        sys.exit(1)
    
    # Check for scheduled mode
    if args.schedule:
        run_scheduled(config, args)
        sys.exit(0)
    
    # Single run mode
    success = run_single_validation(config, args)
    
    if success:
        print("✅ Done.")
        sys.exit(0)
    else:
        print("❌ Validation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
