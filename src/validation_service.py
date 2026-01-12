"""
Main validation service orchestrating data fetching and Slack notifications.
Compares AppLovin MAX data with individual network data.

Optimized with async/await for parallel network fetching.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

from src.config import Config
from src.fetchers import ApplovinFetcher, FetcherFactory
from src.notifiers import SlackNotifier
from src.exporters import GCSExporter
from src.enums import NetworkName

logger = logging.getLogger(__name__)


class ValidationService:
    """Main service for comparing MAX data with network data."""
    
    # Use NetworkName enum for standardized name mapping
    # Maps various AppLovin network name formats to our internal keys
    @staticmethod
    def _get_network_key(network_name: str) -> Optional[str]:
        """Convert AppLovin network name to internal fetcher key using NetworkName enum."""
        try:
            network_enum = NetworkName.from_api_name(network_name)
            if network_enum is None:
                return None
            return network_enum.value
        except (ValueError, AttributeError):
            return None
    
    # Display name mapping - convert AppLovin network names to display names for Slack
    NETWORK_DISPLAY_NAME_MAP = {
        # Vungle -> Liftoff
        'Vungle Bidding': 'Liftoff Bidding',
        'Vungle': 'Liftoff Bidding',
        'VUNGLE_BIDDING': 'Liftoff Bidding',
        'VUNGLE': 'Liftoff Bidding',
        'Liftoff Monetize Bidding': 'Liftoff Bidding',
        # Fyber -> DT Exchange
        'Fyber Bidding': 'DT Exchange Bidding',
        'Fyber': 'DT Exchange Bidding',
        'FYBER_BIDDING': 'DT Exchange Bidding',
        'FYBER': 'DT Exchange Bidding',
        # Tiktok -> Pangle
        'Tiktok Bidding': 'Pangle Bidding',
        'Tiktok': 'Pangle Bidding',
        'TIKTOK_BIDDING': 'Pangle Bidding',
        'TIKTOK': 'Pangle Bidding',
        'TikTok Bidding': 'Pangle Bidding',
        'TikTok': 'Pangle Bidding',
        # Facebook -> Meta
        'Facebook Network': 'Meta Bidding',
        'Facebook Bidding': 'Meta Bidding',
        'FACEBOOK': 'Meta Bidding',
        'FACEBOOK_BIDDING': 'Meta Bidding',
        # ironSource -> Ironsource (standardize casing)
        'ironSource Bidding': 'Ironsource Bidding',
        'ironSource': 'Ironsource Bidding',
        'IronSource Bidding': 'Ironsource Bidding',
        'IronSource': 'Ironsource Bidding',
        # InMobi -> Inmobi (standardize casing)
        'InMobi Bidding': 'Inmobi Bidding',
        'InMobi': 'Inmobi Bidding',
        # BidMachine -> Bidmachine (standardize casing)
        'BidMachine Bidding': 'Bidmachine Bidding',
        'BidMachine': 'Bidmachine Bidding',
        # HyprMX
        'Hyprmx Network': 'HyprMX',
        'HYPRMX_NETWORK': 'HyprMX',
    }
    
    def __init__(self, config: Config):
        """Initialize validation service."""
        self.config = config
        self.applovin_fetcher = None
        self.network_fetchers: Dict[str, Any] = {}
        self.notifier = None
        self.gcs_exporter: Optional[GCSExporter] = None
        
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize fetchers and notifier based on configuration."""
        # Initialize Applovin Max fetcher (source of MAX data)
        applovin_config = self.config.get_applovin_config()
        if applovin_config and applovin_config.get('api_key'):
            self.applovin_fetcher = ApplovinFetcher(
                api_key=applovin_config['api_key'],
                applications=applovin_config.get('applications', [])
            )
        
        # Initialize Network fetchers (source of Network data)
        self._initialize_network_fetchers()
        
        # Initialize Slack notifier
        slack_config = self.config.get_slack_config()
        if slack_config and slack_config.get('webhook_url'):
            self.notifier = SlackNotifier(
                webhook_url=slack_config['webhook_url'],
                channel=slack_config.get('channel')
            )
        
        # Initialize GCS exporter for BigQuery/Looker analytics
        gcp_config = self.config.get_gcp_config()
        if gcp_config and gcp_config.get('enabled'):
            try:
                self.gcs_exporter = GCSExporter(
                    project_id=gcp_config['project_id'],
                    bucket_name=gcp_config['bucket_name'],
                    service_account_path=gcp_config.get('service_account_path'),
                    base_path=gcp_config.get('base_path', 'network_data')
                )
                logger.info(f"GCS exporter initialized (bucket: {gcp_config['bucket_name']})")
            except Exception as e:
                logger.warning(f"GCS exporter initialization failed: {e}")
    
    def _initialize_network_fetchers(self):
        """Initialize individual network fetchers using the FetcherFactory."""
        self.network_fetchers = FetcherFactory.create_all_fetchers(self.config)
    
    async def run_validation(self, start_date=None, end_date=None) -> Dict[str, Any]:
        """
        Run network comparison report with parallel network fetching.
        
        Uses asyncio.gather to fetch data from all networks concurrently,
        significantly reducing total execution time.
        
        Args:
            start_date: Optional start date for backfill (default: yesterday)
            end_date: Optional end date for backfill (default: yesterday)
        """
        from datetime import timezone
        
        now_utc = datetime.now(timezone.utc)
        logger.info(f"Starting Network Comparison Report at {now_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"[{now_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC] Starting Network Comparison Report...")
        print("=" * 80)
        
        # Calculate date range - 1 day delay for data availability (UTC)
        validation_config = self.config.get_validation_config()
        date_range_days = validation_config.get('date_range_days', 1)
        
        # Use provided dates or default to yesterday
        if start_date and end_date:
            # Backfill mode - use provided dates
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
            end_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
            # In backfill mode, Meta also uses the same date (not T-3)
            meta_start_date = start_date
            meta_end_date = end_date
            meta_delay_days = 0  # No delay in backfill mode
        else:
            # Normal mode - use yesterday
            end_date = now_utc.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
            start_date = end_date - timedelta(days=date_range_days - 1)
            # Meta requires delay for stable daily data - use fetcher's configured delay
            from .fetchers.meta_fetcher import MetaFetcher
            meta_delay_days = MetaFetcher.DATA_DELAY_DAYS
            meta_end_date = now_utc.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=meta_delay_days)
            meta_start_date = meta_end_date - timedelta(days=date_range_days - 1)
        
        print(f"📅 Date range (UTC): {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        if meta_delay_days > 0:
            print(f"📅 Meta date range (UTC, T-{meta_delay_days} daily mode): {meta_start_date.strftime('%Y-%m-%d')} to {meta_end_date.strftime('%Y-%m-%d')}")
        print("=" * 80)
        
        if not self.applovin_fetcher:
            logger.error("AppLovin fetcher not configured")
            print("❌ AppLovin fetcher not configured")
            return {'success': False, 'message': 'AppLovin fetcher not configured'}
        
        # Step 1: Fetch MAX data from AppLovin (sync for now, can be converted later)
        print(f"\n📊 Step 1: Fetching AppLovin MAX data...")
        try:
            max_data = await self.applovin_fetcher.fetch_data(start_date, end_date)
            max_rows = max_data.get('comparison_rows', [])
            logger.info(f"Retrieved {len(max_rows)} rows from MAX")
            print(f"   ✅ Retrieved {len(max_rows)} rows from MAX ({start_date.strftime('%Y-%m-%d')})")
        except Exception as e:
            logger.error(f"Failed to fetch MAX data: {e}")
            print(f"   ❌ Error: {str(e)}")
            return {'success': False, 'message': f'Failed to fetch MAX data: {str(e)}'}
        
        # Step 1b: Fetch separate MAX data for Meta using T-3 dates
        max_rows_meta = []
        if 'meta' in self.network_fetchers:
            try:
                print(f"   📥 Fetching MAX data for Meta (T-3: {meta_end_date.strftime('%Y-%m-%d')})...")
                max_data_meta = await self.applovin_fetcher.fetch_data(meta_start_date, meta_end_date)
                max_rows_meta = max_data_meta.get('comparison_rows', [])
                logger.info(f"Retrieved {len(max_rows_meta)} rows from MAX for Meta comparison")
                print(f"   ✅ Retrieved {len(max_rows_meta)} rows from MAX for Meta comparison")
            except Exception as e:
                logger.warning(f"Failed to fetch MAX data for Meta: {e}")
                print(f"   ⚠️ Failed to fetch MAX data for Meta: {str(e)}")
                max_rows_meta = []
        
        # Step 2: Fetch data from all networks IN PARALLEL (main optimization)
        print(f"\n📊 Step 2: Fetching data from {len(self.network_fetchers)} networks in parallel...")
        
        network_data = await self._fetch_all_networks_parallel(
            start_date, end_date, 
            meta_start_date, meta_end_date
        )
        
        # Step 3: Merge MAX data with Network data
        print(f"\n📊 Step 3: Comparing MAX vs Network data...")
        
        # Merge standard networks with standard MAX data
        comparison_rows = self._merge_data(max_rows, network_data, exclude_networks=['meta'])
        
        # Merge Meta with shifted MAX data
        if max_rows_meta and 'meta' in network_data:
            meta_comparison_rows = self._merge_data(max_rows_meta, network_data, include_networks=['meta'])
            comparison_rows.extend(meta_comparison_rows)
        
        # Sort all rows
        comparison_rows.sort(key=lambda x: (x['network'], x['application']))
        
        logger.info(f"Generated {len(comparison_rows)} comparison rows")
        print(f"   ✅ Generated {len(comparison_rows)} comparison rows")
        
        # Calculate totals
        totals = self._calculate_totals(comparison_rows)
        
        # Display table
        if comparison_rows:
            print(f"\n{'=' * 80}")
            print("📈 NETWORK COMPARISON REPORT")
            print("=" * 80)
            
            table = self._generate_comparison_table(comparison_rows)
            print(table)
            
            # Send to Slack
            if self.notifier:
                print("\n📤 Sending report to Slack...")
                threshold = self.config.get_slack_revenue_delta_threshold()
                min_revenue = self.config.get_slack_min_revenue_for_alerts()
                success = self.notifier.send_comparison_report(
                    comparison_rows=comparison_rows,
                    totals=totals,
                    end_date=end_date,
                    network_data=network_data,
                    threshold=threshold,
                    min_revenue=min_revenue,
                    network_key_resolver=self._get_network_key
                )
                if success:
                    logger.info("Report sent to Slack successfully")
                    print("   ✅ Report sent successfully")
                else:
                    logger.error("Failed to send report to Slack")
                    print("   ❌ Failed to send report")
            
            # Export to GCS for BigQuery/Looker analytics
            if self.gcs_exporter:
                print("\n📤 Exporting data to GCS...")
                try:
                    gcs_files = self.gcs_exporter.export_to_gcs(comparison_rows, end_date)
                    if gcs_files:
                        logger.info(f"Exported {len(comparison_rows)} comparison rows to GCS")
                        print(f"   ✅ Exported {len(comparison_rows)} comparison rows to GCS")
                        for f in gcs_files:
                            print(f"      📁 {f}")
                    else:
                        print("   ⚠️ No data exported to GCS")
                except Exception as e:
                    logger.error(f"GCS export failed: {e}")
                    print(f"   ❌ GCS export failed: {e}")
            
            return {
                'success': True,
                'comparison_rows': comparison_rows,
                'totals': totals,
                'timestamp': datetime.now().isoformat()
            }
        else:
            print("\n⚠️  No comparison data available")
            return {'success': True, 'message': 'No comparison data available'}
    
    async def _fetch_all_networks_parallel(
        self,
        start_date: datetime,
        end_date: datetime,
        meta_start_date: datetime,
        meta_end_date: datetime
    ) -> Dict[str, Any]:
        """
        Fetch data from all configured networks in parallel using asyncio.gather.
        
        This is the key performance optimization - instead of sequential API calls
        taking ~30-60 seconds total (12 networks × 3-5s each), parallel calls 
        complete in ~5-8 seconds.
        
        Args:
            start_date: Start date for standard networks
            end_date: End date for standard networks
            meta_start_date: Start date for Meta (T-3)
            meta_end_date: End date for Meta (T-3)
            
        Returns:
            Dictionary mapping network names to their fetched data
        """
        import time
        start_time = time.time()
        
        # Networks that may need fallback to earlier dates
        fallback_networks = {'meta', 'admob', 'dt_exchange'}
        max_fallback_days = 2  # Try up to 2 days earlier if data is empty
        
        async def fetch_network_with_fallback(network_name: str, fetcher) -> Tuple[str, Optional[Dict[str, Any]]]:
            """Fetch data from a single network with fallback for empty results."""
            try:
                # Determine initial date range
                if network_name == 'meta':
                    fetch_start = meta_start_date
                    fetch_end = meta_end_date
                else:
                    fetch_start = start_date
                    fetch_end = end_date
                
                # Try fetching with fallback for networks that may have delayed data
                data = await fetcher.fetch_data(fetch_start, fetch_end)
                
                # Check if data is empty and network supports fallback
                if network_name in fallback_networks and data.get('impressions', 0) == 0:
                    # Try earlier dates
                    for fallback_day in range(1, max_fallback_days + 1):
                        earlier_date = fetch_end - timedelta(days=fallback_day)
                        logger.info(f"{network_name}: No data for {fetch_end.strftime('%Y-%m-%d')}, trying {earlier_date.strftime('%Y-%m-%d')}...")
                        print(f"   ⏳ {network_name}: No data, trying {earlier_date.strftime('%Y-%m-%d')}...")
                        
                        data = await fetcher.fetch_data(earlier_date, earlier_date)
                        if data.get('impressions', 0) > 0:
                            logger.info(f"{network_name}: Found data for {earlier_date.strftime('%Y-%m-%d')}")
                            break
                
                date_range = data.get('date_range', {})
                date_info = f"({date_range.get('start', '?')} to {date_range.get('end', '?')})"
                logger.info(f"{network_name}: ${data.get('revenue', 0):.2f} revenue, {data.get('impressions', 0):,} imps {date_info}")
                print(f"   ✅ {network_name}: ${data.get('revenue', 0):.2f} revenue, {data.get('impressions', 0):,} imps {date_info}")
                return (network_name, data)
            except Exception as e:
                logger.error(f"{network_name} error: {e}")
                print(f"   ❌ {network_name} error: {str(e)}")
                return (network_name, None)
            finally:
                # Ensure session is closed
                if hasattr(fetcher, 'close'):
                    try:
                        await fetcher.close()
                    except Exception:
                        pass
        
        # Create tasks for all networks
        tasks = [
            fetch_network_with_fallback(network_name, fetcher)
            for network_name, fetcher in self.network_fetchers.items()
        ]
        
        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        network_data = {}
        failed_networks = []  # Track failed networks for alerting
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Unexpected error in parallel fetch: {result}")
                continue
            network_name, data = result
            if data is not None:
                network_data[network_name] = data
            else:
                failed_networks.append(network_name)
        
        # Store failed networks in result for Slack notification
        if failed_networks:
            network_data['_failed_networks'] = failed_networks
            logger.warning(f"Failed to fetch data from: {', '.join(failed_networks)}")
            print(f"   ⚠️ Failed networks: {', '.join(failed_networks)}")
        
        # Also close AppLovin fetcher session
        if self.applovin_fetcher and hasattr(self.applovin_fetcher, 'close'):
            try:
                await self.applovin_fetcher.close()
            except Exception:
                pass
        
        elapsed = time.time() - start_time
        successful_count = len([k for k in network_data.keys() if not k.startswith('_')])
        logger.info(f"Parallel fetch completed in {elapsed:.2f}s for {successful_count}/{len(self.network_fetchers)} networks")
        print(f"   ⏱️ Parallel fetch completed in {elapsed:.2f}s")
        
        return network_data
    
    def _merge_data(self, max_rows: List[Dict], network_data: Dict[str, Any], 
                     exclude_networks: List[str] = None, include_networks: List[str] = None) -> List[Dict]:
        """
        Merge MAX data with network data for comparison.
        
        Args:
            max_rows: MAX data rows from AppLovin
            network_data: Network data from individual fetchers
            exclude_networks: List of network keys to exclude (e.g., ['meta'])
            include_networks: List of network keys to include only (e.g., ['meta'])
        """
        comparison_rows = []
        exclude_networks = exclude_networks or []
        
        for row in max_rows:
            network_name = row.get('network', '')
            network_key = self._get_network_key(network_name)
            
            platform = 'ios' if 'iOS' in row.get('application', '') else 'android'
            ad_type = row.get('ad_type', '').lower()
            
            # Special handling for AppLovin's own networks (Applovin Bidding, Applovin Exchange)
            # For these networks, MAX data IS the network's own data - no separate API needed
            is_applovin_network = 'applovin' in network_name.lower()
            
            if is_applovin_network:
                # Skip Applovin networks if we're doing include_networks filter (e.g., Meta-only pass)
                # This prevents Applovin from being added twice
                if include_networks:
                    continue
                    
                # Use MAX values as network values since AppLovin reports its own data directly
                net_revenue = row.get('max_revenue', 0)
                net_impressions = row.get('max_impressions', 0)
                net_ecpm = row.get('max_ecpm', 0)
            else:
                # Only include networks that have fetchers configured
                if not network_key or network_key not in network_data:
                    continue
                
                # Apply include/exclude filters
                if include_networks and network_key not in include_networks:
                    continue
                if network_key in exclude_networks:
                    continue
                
                net_data = network_data[network_key]
                
                # Get platform-specific data
                platform_data = net_data.get('platform_data', {}).get(platform, {})
                ad_data = platform_data.get('ad_data', {}).get(ad_type, {})
                
                # Skip if no network data for this ad type
                if ad_data.get('impressions', 0) == 0:
                    continue
                
                net_revenue = ad_data.get('revenue', 0)
                net_impressions = ad_data.get('impressions', 0)
                net_ecpm = ad_data.get('ecpm', 0)
            
            # Calculate deltas
            imp_delta = self._calculate_delta(row['max_impressions'], net_impressions)
            rev_delta = self._calculate_delta(row['max_revenue'], net_revenue)
            cpm_delta = self._calculate_delta(row['max_ecpm'], net_ecpm)
            
            # Get display name for network (convert Vungle -> Liftoff etc.)
            display_network = self.NETWORK_DISPLAY_NAME_MAP.get(row['network'], row['network'])
            
            # Get report date for this network (for date labeling in Slack)
            report_date = None
            if network_key and network_key in network_data:
                date_range = network_data[network_key].get('date_range', {})
                report_date = date_range.get('end') or date_range.get('start')
            
            comparison_rows.append({
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
                'report_date': report_date,  # Date label for Slack report
            })
        
        # Sort by application, then network
        comparison_rows.sort(key=lambda x: (x['network'], x['application']))
        
        return comparison_rows
    
    def _calculate_delta(self, max_val: float, network_val: float) -> str:
        """Calculate delta percentage."""
        if max_val == 0 and network_val == 0:
            return "0.0%"
        elif max_val == 0:
            return "+∞%"
        
        delta = ((network_val - max_val) / max_val) * 100
        sign = "+" if delta > 0 else ""
        return f"{sign}{delta:.1f}%"
    
    def _calculate_totals(self, comparison_rows: List[Dict]) -> Dict:
        """Calculate totals from comparison rows."""
        totals = {
            'max_revenue': sum(r['max_revenue'] for r in comparison_rows),
            'network_revenue': sum(r['network_revenue'] for r in comparison_rows),
            'max_impressions': sum(r['max_impressions'] for r in comparison_rows),
            'network_impressions': sum(r['network_impressions'] for r in comparison_rows),
        }
        return totals
    
    def _generate_comparison_table(self, comparison_rows: List[Dict]) -> str:
        """Generate comparison table for terminal output."""
        lines = []
        
        # Header
        lines.append(f"{'Application':<28} │ {'Network':<18} │ {'Ad Type':<12} │ {'MAX Imps':>10} │ {'Net Imps':>10} │ {'Imp Δ':>8} │ {'MAX Rev':>10} │ {'Net Rev':>10} │ {'Rev Δ':>8} │ {'MAX CPM':>8} │ {'Net CPM':>8} │ {'CPM Δ':>8}")
        lines.append("─" * 180)
        
        for row in comparison_rows:
            lines.append(
                f"{row['application']:<28} │ "
                f"{row['network']:<18} │ "
                f"{row['ad_type']:<12} │ "
                f"{row['max_impressions']:>10,} │ "
                f"{row['network_impressions']:>10,} │ "
                f"{row['imp_delta']:>8} │ "
                f"${row['max_revenue']:>9,.2f} │ "
                f"${row['network_revenue']:>9,.2f} │ "
                f"{row['rev_delta']:>8} │ "
                f"${row['max_ecpm']:>7,.2f} │ "
                f"${row['network_ecpm']:>7,.2f} │ "
                f"{row['cpm_delta']:>8}"
            )
        
        return "\n".join(lines)
    

        if not self.notifier:
            print("Slack notifier not configured")
            return False
        
        print("Sending test message to Slack...")
        success = self.notifier.send_test_message()
        print("✅ Test message sent" if success else "❌ Failed")
        return success

