"""
Main entry point for the Network Data Validation System.

Optimized with asyncio for parallel network fetching.

Modes:
    - Default: Run validation once and exit
    - --schedule: Run on schedule from config
    - --schedule-now: Run immediately then schedule
    - --report: Generate 7-day reports for all networks, send to Slack and GCS
    - --test-slack: Test Slack connection
"""
import sys
import io
import time
import asyncio
import logging
import schedule
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple, Set

from src.config import Config
from src.validation_service import ValidationService
from src.fetchers import ApplovinFetcher, FetcherFactory
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
# Network Reporter - Generates 7-day reports based on AppLovin MAX data
# =============================================================================

# Display name mapping - convert AppLovin network names to display names
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


def _calculate_date_range(config: Config, end_date: datetime, start_date: datetime = None) -> Tuple[datetime, datetime]:
    """
    Calculate date range for report.
    
    If start_date is provided, use it directly.
    Otherwise, calculate based on date_range_days from config (default 7 days).
    
    Args:
        config: Config instance
        end_date: End date for the report
        start_date: Optional start date. If None, calculated as end_date - (date_range_days - 1)
    """
    now_utc = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = now_utc - timedelta(days=1)
    
    if end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=timezone.utc)
    
    adjusted_end = min(end_date, yesterday)
    adjusted_end = adjusted_end.replace(hour=0, minute=0, second=0, microsecond=0)
    
    if start_date is not None:
        # Use provided start_date
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        # Calculate from config
        validation_config = config.get_validation_config()
        date_range_days = validation_config.get('date_range_days', 7)
        start_date = adjusted_end - timedelta(days=date_range_days - 1)
    
    return start_date, adjusted_end


def _extract_networks_from_max(max_rows: List[Dict]) -> Dict[str, Set[str]]:
    """Extract unique networks from MAX data grouped by their fetcher key."""
    networks: Dict[str, Set[str]] = {}
    
    for row in max_rows:
        network_name = row.get('network', '')
        network_key = _get_network_key(network_name)
        
        if network_key:
            if network_key not in networks:
                networks[network_key] = set()
            networks[network_key].add(network_name)
        else:
            if network_name not in networks:
                networks[network_name] = set()
            networks[network_name].add(network_name)
    
    return networks


def _create_comparison_rows(
    max_rows: List[Dict],
    network_data: Dict[str, Any],
    failed_networks: Set[str]
) -> List[Dict]:
    """Create comparison rows from MAX data merged with network data."""
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


async def generate_report(
    end_date: datetime,
    config: Config,
    start_date: datetime = None
) -> Dict[str, Any]:
    """
    Generate report based on AppLovin MAX data.
    
    AppLovin MAX is the single source of truth. All networks visible in MAX
    are included. Network API data is fetched for comparison where available.
    
    Args:
        end_date: End date for the report (capped to T-1)
        config: Config instance
        start_date: Optional start date. If None, uses end_date - 6 days (7 days total)
    """
    # Initialize AppLovin fetcher
    applovin_config = config.get_applovin_config()
    if not applovin_config or not applovin_config.get('api_key'):
        return {
            'success': False,
            'error': 'AppLovin fetcher not configured'
        }
    
    applovin_fetcher = ApplovinFetcher(
        api_key=applovin_config['api_key'],
        applications=applovin_config.get('applications', [])
    )
    
    networks_config = config.get_networks_config()
    
    # Calculate date range (same for all networks)
    calc_start, adjusted_end = _calculate_date_range(config, end_date, start_date)
    
    print(f"\n{'=' * 60}")
    print(f"📊 REPORT GENERATION")
    print(f"{'=' * 60}")
    print(f"📅 Date range: {calc_start.strftime('%Y-%m-%d')} to {adjusted_end.strftime('%Y-%m-%d')}")
    
    # Step 1: Fetch MAX data
    print(f"\n📥 Step 1: Fetching AppLovin MAX data...")
    try:
        max_data = await applovin_fetcher.fetch_data(calc_start, adjusted_end)
        max_rows = max_data.get('comparison_rows', [])
        print(f"   ✅ MAX: {len(max_rows)} rows")
    except Exception as e:
        logger.error(f"Failed to fetch MAX data: {e}")
        print(f"   ❌ Failed to fetch MAX data: {e}")
        return {
            'success': False,
            'error': f'Failed to fetch MAX data: {str(e)}'
        }
    
    if not max_rows:
        print("   ⚠️ No MAX data available")
        return {
            'success': True,
            'comparison_rows': [],
            'last_day_rows': [],
            'message': 'No MAX data available'
        }
    
    # Step 2: Extract unique networks from MAX data
    networks_in_max = _extract_networks_from_max(max_rows)
    print(f"\n📊 Step 2: Networks found in MAX data: {len(networks_in_max)}")
    for net_key, net_names in sorted(networks_in_max.items()):
        print(f"   • {net_key}: {', '.join(net_names)}")
    
    # Step 3: Determine which networks to fetch
    networks_to_fetch = []
    
    for network_key in networks_in_max.keys():
        network_config = networks_config.get(network_key, {})
        if network_config.get('enabled', False):
            networks_to_fetch.append(network_key)
    
    print(f"\n📥 Step 3: Fetching data from {len(networks_to_fetch)} networks with API integration...")
    if networks_to_fetch:
        print(f"   Networks: {', '.join(networks_to_fetch)}")
    
    # Step 4: Fetch network data in parallel
    network_data: Dict[str, Any] = {}
    failed_networks: Set[str] = set()
    
    async def fetch_single_network(network_key: str) -> Tuple[str, Optional[Dict]]:
        """Fetch data for a single network."""
        network_config = networks_config.get(network_key, {})
        
        fetcher = FetcherFactory.create_fetcher(network_key, network_config)
        if not fetcher:
            return (network_key, None)
        
        try:
            data = await fetcher.fetch_data(calc_start, adjusted_end)
            daily_data = data.get('daily_data', {})
            days_with_data = len(daily_data)
            
            print(f"   ✅ {network_key}: ${data.get('revenue', 0):.2f} revenue, {data.get('impressions', 0):,} impressions ({days_with_data} days with data)")
            return (network_key, data)
        except Exception as e:
            logger.error(f"Error fetching {network_key}: {e}")
            print(f"   ❌ {network_key}: {str(e)}")
            return (network_key, None)
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
            network_key, data = result
            if data is not None:
                network_data[network_key] = data
            else:
                failed_networks.add(network_key)
    
    # Close AppLovin fetcher
    if hasattr(applovin_fetcher, 'close'):
        try:
            await applovin_fetcher.close()
        except Exception:
            pass
    
    # Step 5: Create comparison rows
    print(f"\n📊 Step 4: Creating comparison report...")
    comparison_rows = _create_comparison_rows(max_rows, network_data, failed_networks)
    
    # Filter last day rows
    last_date = adjusted_end.strftime('%Y-%m-%d')
    last_day_rows = [row for row in comparison_rows if row.get('date') == last_date]
    
    # Summary
    rows_with_network_data = sum(1 for r in comparison_rows if r.get('has_network_data', False))
    rows_without_network_data = len(comparison_rows) - rows_with_network_data
    
    print(f"   ✅ Total comparison rows: {len(comparison_rows)}")
    print(f"   ✅ Rows with network data: {rows_with_network_data}")
    print(f"   ⚠️ Rows without network data (MAX only): {rows_without_network_data}")
    print(f"   ✅ Last day ({last_date}) rows: {len(last_day_rows)}")
    
    # Networks without API integration
    networks_without_api = set(networks_in_max.keys()) - set(networks_to_fetch) - {'applovin'}
    networks_without_api = {n for n in networks_without_api if not n.startswith('Applovin')}
    
    if networks_without_api:
        print(f"\n   ℹ️ Networks without API integration: {', '.join(sorted(networks_without_api))}")
    
    if failed_networks:
        print(f"   ⚠️ Failed to fetch: {', '.join(sorted(failed_networks))}")
    
    return {
        'success': True,
        'comparison_rows': comparison_rows,
        'last_day_rows': last_day_rows,
        'date_range': {
            'start': calc_start.strftime('%Y-%m-%d'),
            'end': adjusted_end.strftime('%Y-%m-%d')
        },
        'networks_in_max': list(networks_in_max.keys()),
        'networks_fetched': list(network_data.keys()),
        'networks_failed': list(failed_networks),
        'networks_without_api': list(networks_without_api) if networks_without_api else [],
        'network_data': network_data
    }


# =============================================================================
# Validation Functions
# =============================================================================

def run_validation_check(service: ValidationService, start_date=None, end_date=None):
    """Run a single validation check."""
    try:
        print("\n" + "=" * 60)
        result = asyncio.run(service.run_validation(start_date=start_date, end_date=end_date))
        print("=" * 60 + "\n")
        
        if not result['success']:
            logger.error(f"Validation check failed: {result.get('message', 'Unknown error')}")
            print(f"Validation check failed: {result.get('message', 'Unknown error')}")
    except Exception as e:
        logger.error(f"Error during validation check: {e}", exc_info=True)
        print(f"Error during validation check: {str(e)}")


def run_report_mode(config: Config, start_date: datetime = None, end_date: datetime = None):
    """
    Run report mode - generate reports based on AppLovin MAX data.
    
    AppLovin MAX is the single source of truth. All networks in MAX are included.
    Sends last day's data to Slack and exports all data to GCS for Looker.
    
    Args:
        config: Config instance
        start_date: Optional start date. If None, uses end_date - 6 days
        end_date: Optional end date. If None, uses today (capped to T-1)
    """
    from src.notifiers import SlackNotifier
    from src.exporters import GCSExporter
    
    print("\n" + "=" * 60)
    print("📊 REPORT MODE - AppLovin MAX Based Reports")
    print("=" * 60)
    
    # Default end_date to today if not specified
    if end_date is None:
        end_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    elif end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=timezone.utc)
    
    if start_date is not None and start_date.tzinfo is None:
        start_date = start_date.replace(tzinfo=timezone.utc)
    
    if start_date:
        print(f"📅 Report date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    else:
        print(f"📅 Report end date: {end_date.strftime('%Y-%m-%d')} (last 7 days)")
    
    # Generate report
    result = asyncio.run(generate_report(end_date, config, start_date))
    
    if not result.get('success'):
        print(f"❌ Report generation failed: {result.get('error', 'Unknown error')}")
        return
    
    # Get comparison rows
    all_comparison_rows = result.get('comparison_rows', [])
    all_last_day_rows = result.get('last_day_rows', [])
    network_data = result.get('network_data', {})
    
    # Track failed and missing networks
    failed_networks = result.get('networks_failed', [])
    networks_without_api = result.get('networks_without_api', [])
    
    if failed_networks:
        network_data['_failed_networks'] = failed_networks
    
    print(f"\n📊 Total comparison rows: {len(all_comparison_rows)}")
    print(f"📊 Last day rows (for Slack): {len(all_last_day_rows)}")
    
    # Send last day's report to Slack (only rows with network data)
    slack_config = config.get_slack_config()
    if slack_config and slack_config.get('webhook_url') and all_last_day_rows:
        print("\n📤 Sending last day report to Slack...")
        
        notifier = SlackNotifier(
            webhook_url=slack_config['webhook_url'],
            channel=slack_config.get('channel')
        )
        
        threshold = config.get_slack_revenue_delta_threshold()
        min_revenue = config.get_slack_min_revenue_for_alerts()
        
        # Filter rows with network data for Slack
        slack_rows = [r for r in all_last_day_rows if r.get('has_network_data', False)]
        
        # Calculate totals
        totals = {
            'max_revenue': sum(r['max_revenue'] for r in slack_rows),
            'network_revenue': sum(r.get('network_revenue', 0) or 0 for r in slack_rows),
            'max_impressions': sum(r['max_impressions'] for r in slack_rows),
            'network_impressions': sum(r.get('network_impressions', 0) or 0 for r in slack_rows),
        }
        
        # Get the last date from rows
        dates = sorted(set(row.get('date', '') for row in all_last_day_rows if row.get('date')))
        report_end_date = datetime.strptime(dates[-1], '%Y-%m-%d') if dates else end_date
        
        # Define network key resolver
        def network_key_resolver(network_name: str):
            try:
                network_enum = NetworkName.from_api_name(network_name)
                return network_enum.value if network_enum else None
            except (ValueError, AttributeError):
                return None
        
        success = notifier.send_comparison_report(
            comparison_rows=slack_rows,
            totals=totals,
            end_date=report_end_date,
            network_data=network_data,
            threshold=threshold,
            min_revenue=min_revenue,
            network_key_resolver=network_key_resolver
        )
        
        if success:
            print(f"   ✅ Last day report sent to Slack ({len(slack_rows)} rows with network data)")
        else:
            print("   ❌ Failed to send report to Slack")
    else:
        print("\n⚠️ Slack not configured or no last day data")
    
    # Export 7-day data to GCS for Looker
    gcp_config = config.get_gcp_config()
    if gcp_config and gcp_config.get('enabled') and all_comparison_rows:
        print("\n📤 Exporting 7-day data to GCS...")
        
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
        print("\n⚠️ GCS not configured or no comparison data")
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ Report mode complete")
    if networks_without_api:
        print(f"   ℹ️ Networks without API: {', '.join(sorted(networks_without_api))}")
    if failed_networks:
        print(f"   ⚠️ Failed networks: {', '.join(sorted(failed_networks))}")
    print("=" * 60 + "\n")


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main function."""
    print("Network Data Validation System")
    print("=" * 60)
    
    # Check command line arguments first
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("\nKullanım:")
        print("  python main.py              - Bir kez çalıştır ve çık (varsayılan)")
        print("  python main.py --schedule   - Zamanlamayı başlat (config.yaml'dan interval ve start_time)")
        print("  python main.py --schedule-now - Önce çalıştır, sonra zamanlamayı başlat")
        print("  python main.py --report     - Son 7 günlük rapor oluştur (T-8 to T-1)")
        print("  python main.py --report --end-date 2026-01-17 - Belirli bitiş tarihi için rapor (son 7 gün)")
        print("  python main.py --report --start-date 2026-01-01 --end-date 2026-01-17 - Belirli tarih aralığı için rapor")
        print("  python main.py --test-slack - Slack bağlantısını test et")
        print("  python main.py --start-date 2026-01-01 --end-date 2026-01-10 - Belirli tarih aralığı için backfill (validation)")
        print("  python main.py --help       - Bu yardım mesajını göster")
        print("\nZamanlama ayarları config.yaml'dan okunur:")
        print("  scheduling.interval_hours: Çalışma aralığı (saat)")
        print("  scheduling.start_time: Başlangıç saati (HH:MM)")
        sys.exit(0)
    
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
    
    # Parse date arguments
    start_date = None
    end_date = None
    
    if '--start-date' in sys.argv:
        idx = sys.argv.index('--start-date')
        if idx + 1 < len(sys.argv):
            start_date = datetime.strptime(sys.argv[idx + 1], '%Y-%m-%d')
    
    if '--end-date' in sys.argv:
        idx = sys.argv.index('--end-date')
        if idx + 1 < len(sys.argv):
            end_date = datetime.strptime(sys.argv[idx + 1], '%Y-%m-%d')
    
    # If start_date provided but not end_date, use start_date as end_date
    if start_date and not end_date:
        end_date = start_date
    
    # Check command line arguments - handle modes that don't need ValidationService first
    if len(sys.argv) > 1:
        if sys.argv[1] == '--report':
            # Report mode - uses its own fetchers, no need for ValidationService
            run_report_mode(config, start_date, end_date)
            sys.exit(0)
    
    # Initialize ValidationService only for modes that need it
    service = ValidationService(config)
    
    # Check remaining command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--test-slack':
            # Test Slack integration
            service.test_slack_integration()
            sys.exit(0)
        elif sys.argv[1] == '--schedule':
            # Run with config-based interval scheduling
            interval_hours = config.get_scheduling_interval_hours()
            scheduled_times = config.get_scheduled_times()
            
            print("\n🕐 Zamanlama aktif!")
            print(f"   📅 Her {interval_hours} saatte bir çalışacak")
            print(f"   🕐 Çalışma saatleri: {', '.join(scheduled_times)}")
            print("   ⏰ Şu anki saat:", datetime.now().strftime("%H:%M:%S"))
            print("\nDurdurmak için Ctrl+C basın\n")
            
            # Schedule at calculated times from config
            for run_time in scheduled_times:
                schedule.every().day.at(run_time).do(lambda: run_validation_check(service))
            
            # Show next run time
            next_run = schedule.next_run()
            if next_run:
                print(f"⏳ Sonraki çalışma zamanı: {next_run.strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            # Keep running
            try:
                while True:
                    schedule.run_pending()
                    time.sleep(30)  # Check every 30 seconds
            except KeyboardInterrupt:
                print("\n\n🛑 Kapatılıyor...")
                sys.exit(0)
        elif sys.argv[1] == '--schedule-now':
            # Run immediately then continue with config-based schedule
            interval_hours = config.get_scheduling_interval_hours()
            scheduled_times = config.get_scheduled_times()
            
            print("\n🕐 Zamanlama aktif (önce bir kez çalıştırılacak)!")
            print(f"   📅 Her {interval_hours} saatte bir çalışacak")
            print(f"   🕐 Çalışma saatleri: {', '.join(scheduled_times)}")
            print("   ⏰ Şu anki saat:", datetime.now().strftime("%H:%M:%S"))
            print("\nDurdurmak için Ctrl+C basın\n")
            
            # Run immediately
            print("🚀 Şimdi çalıştırılıyor...\n")
            run_validation_check(service)
            
            # Schedule at calculated times from config
            for run_time in scheduled_times:
                schedule.every().day.at(run_time).do(lambda: run_validation_check(service))
            
            # Show next run time
            next_run = schedule.next_run()
            if next_run:
                print(f"\n⏳ Sonraki çalışma zamanı: {next_run.strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            # Keep running
            try:
                while True:
                    schedule.run_pending()
                    time.sleep(30)
            except KeyboardInterrupt:
                print("\n\n🛑 Kapatılıyor...")
                sys.exit(0)
    
    # Default: Run once and exit (with optional date range)
    if start_date:
        print(f"\n🔄 Backfill mode: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        current = start_date
        while current <= end_date:
            print(f"\n{'='*60}")
            print(f"📅 Processing: {current.strftime('%Y-%m-%d')}")
            print(f"{'='*60}")
            run_validation_check(service, start_date=current, end_date=current)
            current += timedelta(days=1)
    else:
        run_validation_check(service)
    print("\nDone.")
    sys.exit(0)


if __name__ == "__main__":
    main()
