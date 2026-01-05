"""
Main validation service orchestrating data fetching and Slack notifications.
Compares AppLovin MAX data with individual network data.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List
from src.config import Config
from src.fetchers import ApplovinFetcher, MintegralFetcher, UnityAdsFetcher, AdmobFetcher, MetaFetcher, MolocoFetcher, IronSourceFetcher, InMobiFetcher, BidMachineFetcher, LiftoffFetcher
from src.notifiers import SlackNotifier


class ValidationService:
    """Main service for comparing MAX data with network data."""
    
    # Network name mapping - AppLovin network names to our fetcher names
    NETWORK_NAME_MAP = {
        'MINTEGRAL_BIDDING': 'mintegral',
        'MINTEGRAL': 'mintegral',
        'UNITY_BIDDING': 'unity',
        'UNITY': 'unity',
        'ADMOB_BIDDING': 'admob',
        'ADMOB': 'admob',
        'GOOGLE_BIDDING': 'admob',
        'GOOGLE': 'admob',
        'IRONSOURCE_BIDDING': 'ironsource',
        'IRONSOURCE': 'ironsource',
        'FACEBOOK_NETWORK': 'meta',
        'FACEBOOK_BIDDING': 'meta',
        'FACEBOOK': 'meta',
        'META_AUDIENCE_NETWORK': 'meta',
        'META_BIDDING': 'meta',
        'META': 'meta',
        'MOLOCO_BIDDING': 'moloco',
        'MOLOCO': 'moloco',
        'INMOBI_BIDDING': 'inmobi',
        'INMOBI': 'inmobi',
        'BIDMACHINE_BIDDING': 'bidmachine',
        'BIDMACHINE': 'bidmachine',
        'LIFTOFF_BIDDING': 'liftoff',
        'LIFTOFF': 'liftoff',
        'VUNGLE_BIDDING': 'liftoff',
        'VUNGLE': 'liftoff',
    }
    
    # Display name mapping - convert AppLovin network names to display names for Slack
    NETWORK_DISPLAY_NAME_MAP = {
        'Vungle Bidding': 'Liftoff Bidding',
        'Vungle': 'Liftoff',
        'VUNGLE_BIDDING': 'Liftoff Bidding',
        'VUNGLE': 'Liftoff',
    }
    
    def __init__(self, config: Config):
        """Initialize validation service."""
        self.config = config
        self.applovin_fetcher = None
        self.network_fetchers = {}
        self.notifier = None
        
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
    
    def _initialize_network_fetchers(self):
        """Initialize individual network fetchers."""
        # Mintegral
        mintegral_config = self.config.get_mintegral_config()
        if mintegral_config.get('enabled') and mintegral_config.get('skey'):
            self.network_fetchers['mintegral'] = MintegralFetcher(
                skey=mintegral_config['skey'],
                secret=mintegral_config['secret'],
                app_id=mintegral_config.get('app_ids')
            )
            print(f"   ✅ Mintegral fetcher initialized")
        
        # Unity Ads
        unity_config = self.config.get_unity_config()
        if unity_config.get('enabled') and unity_config.get('api_key'):
            self.network_fetchers['unity'] = UnityAdsFetcher(
                api_key=unity_config['api_key'],
                organization_id=unity_config.get('organization_id'),
                game_ids=unity_config.get('game_ids')
            )
            print(f"   ✅ Unity Ads fetcher initialized")
        
        # Google AdMob (OAuth 2.0)
        admob_config = self.config.get_admob_config()
        if admob_config.get('enabled') and admob_config.get('oauth_credentials_path'):
            try:
                self.network_fetchers['admob'] = AdmobFetcher(
                    publisher_id=admob_config['publisher_id'],
                    app_ids=admob_config.get('app_ids'),
                    oauth_credentials_path=admob_config['oauth_credentials_path'],
                    token_path=admob_config.get('token_path', 'credentials/admob_token.json')
                )
                print(f"   ✅ AdMob fetcher initialized")
            except ImportError as e:
                print(f"   ⚠️ AdMob fetcher skipped: {str(e)}")
            except FileNotFoundError as e:
                print(f"   ⚠️ AdMob fetcher skipped: {str(e)}")
            except Exception as e:
                print(f"   ⚠️ AdMob fetcher skipped: {str(e)}")
        
        # Meta Audience Network
        meta_config = self.config.get_meta_config()
        if meta_config.get('enabled') and meta_config.get('access_token'):
            try:
                self.network_fetchers['meta'] = MetaFetcher(
                    access_token=meta_config['access_token'],
                    business_id=meta_config['business_id']
                )
                print(f"   ✅ Meta Audience Network fetcher initialized")
            except Exception as e:
                print(f"   ⚠️ Meta fetcher skipped: {str(e)}")
        
        # Moloco Publisher
        moloco_config = self.config.get_moloco_config()
        if moloco_config.get('enabled') and moloco_config.get('publisher_id'):
            try:
                self.network_fetchers['moloco'] = MolocoFetcher(
                    email=moloco_config['email'],
                    password=moloco_config['password'],
                    platform_id=moloco_config['platform_id'],
                    publisher_id=moloco_config['publisher_id'],
                    app_bundle_ids=moloco_config.get('app_bundle_ids'),
                    time_zone=moloco_config.get('time_zone', 'UTC'),
                    ad_unit_mapping=moloco_config.get('ad_unit_mapping', {})
                )
                print(f"   ✅ Moloco Publisher fetcher initialized")
            except Exception as e:
                print(f"   ⚠️ Moloco fetcher skipped: {str(e)}")
        
        # IronSource
        ironsource_config = self.config.get_ironsource_config()
        if ironsource_config.get('enabled') and ironsource_config.get('secret_key'):
            try:
                self.network_fetchers['ironsource'] = IronSourceFetcher(
                    username=ironsource_config['username'],
                    secret_key=ironsource_config['secret_key'],
                    android_app_keys=ironsource_config.get('android_app_keys'),
                    ios_app_keys=ironsource_config.get('ios_app_keys'),
                )
                print(f"   ✅ IronSource fetcher initialized")
            except Exception as e:
                print(f"   ⚠️ IronSource fetcher skipped: {str(e)}")
        
        # InMobi
        inmobi_config = self.config.get_inmobi_config()
        if inmobi_config.get('enabled') and inmobi_config.get('secret_key'):
            try:
                self.network_fetchers['inmobi'] = InMobiFetcher(
                    account_id=inmobi_config['account_id'],
                    secret_key=inmobi_config['secret_key'],
                    username=inmobi_config.get('username'),
                    app_ids=inmobi_config.get('app_ids')
                )
                print(f"   ✅ InMobi fetcher initialized")
            except Exception as e:
                print(f"   ⚠️ InMobi fetcher skipped: {str(e)}")
        
        # BidMachine
        bidmachine_config = self.config.get_bidmachine_config()
        if bidmachine_config.get('enabled') and bidmachine_config.get('username'):
            try:
                self.network_fetchers['bidmachine'] = BidMachineFetcher(
                    username=bidmachine_config['username'],
                    password=bidmachine_config['password'],
                    app_bundle_ids=bidmachine_config.get('app_bundle_ids'),
                )
                print(f"   ✅ BidMachine fetcher initialized")
            except Exception as e:
                print(f"   ⚠️ BidMachine fetcher skipped: {str(e)}")
        
        # Liftoff (Vungle)
        liftoff_config = self.config.get_liftoff_config()
        if liftoff_config.get('enabled') and liftoff_config.get('api_key'):
            try:
                self.network_fetchers['liftoff'] = LiftoffFetcher(
                    api_key=liftoff_config['api_key'],
                    application_ids=liftoff_config.get('application_ids'),
                )
                print(f"   ✅ Liftoff fetcher initialized")
            except Exception as e:
                print(f"   ⚠️ Liftoff fetcher skipped: {str(e)}")
    
    def run_validation(self) -> Dict[str, Any]:
        """Run network comparison report."""
        from datetime import timezone
        
        now_utc = datetime.now(timezone.utc)
        print(f"[{now_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC] Starting Network Comparison Report...")
        print("=" * 80)
        
        # Calculate date range - 1 day delay for data availability (UTC)
        validation_config = self.config.get_validation_config()
        date_range_days = validation_config.get('date_range_days', 1)
        end_date = now_utc.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        start_date = end_date - timedelta(days=date_range_days - 1)
        
        # Meta has 3-day reporting delay - calculate shifted dates
        meta_delay_days = 3
        meta_end_date = end_date - timedelta(days=meta_delay_days)
        meta_start_date = start_date - timedelta(days=meta_delay_days)
        
        print(f"📅 Date range (UTC): {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"📅 Meta date range (UTC, {meta_delay_days}-day delay): {meta_start_date.strftime('%Y-%m-%d')} to {meta_end_date.strftime('%Y-%m-%d')}")
        print("=" * 80)
        
        if not self.applovin_fetcher:
            print("❌ AppLovin fetcher not configured")
            return {'success': False, 'message': 'AppLovin fetcher not configured'}
        
        # Step 1: Fetch MAX data from AppLovin for standard networks
        print(f"\n📊 Step 1: Fetching AppLovin MAX data...")
        try:
            max_data = self.applovin_fetcher.fetch_data(start_date, end_date)
            max_rows = max_data.get('comparison_rows', [])
            print(f"   ✅ Retrieved {len(max_rows)} rows from MAX ({start_date.strftime('%Y-%m-%d')})")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            return {'success': False, 'message': f'Failed to fetch MAX data: {str(e)}'}
        
        # Step 1b: Fetch MAX data for Meta with shifted date range
        max_rows_meta = []
        if 'meta' in self.network_fetchers:
            print(f"   📥 Fetching MAX data for Meta comparison ({meta_start_date.strftime('%Y-%m-%d')} to {meta_end_date.strftime('%Y-%m-%d')})...")
            try:
                max_data_meta = self.applovin_fetcher.fetch_data(meta_start_date, meta_end_date)
                max_rows_meta = max_data_meta.get('comparison_rows', [])
                print(f"   ✅ Retrieved {len(max_rows_meta)} rows from MAX for Meta comparison")
            except Exception as e:
                print(f"   ⚠️ Could not fetch META comparison data: {str(e)}")
        
        # Step 2: Fetch data from each enabled network
        print(f"\n📊 Step 2: Fetching data from individual networks...")
        network_data = {}
        
        for network_name, fetcher in self.network_fetchers.items():
            try:
                print(f"   📥 Fetching {network_name}...")
                # Use appropriate date range for each network
                if network_name == 'meta':
                    data = fetcher.fetch_data(meta_start_date, meta_end_date)
                else:
                    data = fetcher.fetch_data(start_date, end_date)
                network_data[network_name] = data
                date_range = data.get('date_range', {})
                date_info = f"({date_range.get('start', '?')} to {date_range.get('end', '?')})"
                print(f"      ✅ {network_name}: ${data.get('revenue', 0):.2f} revenue, {data.get('impressions', 0):,} imps {date_info}")
            except Exception as e:
                print(f"      ❌ {network_name} error: {str(e)}")
        
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
                success = self._send_slack_report(comparison_rows, totals, start_date, end_date, network_data)
                if success:
                    print("   ✅ Report sent successfully")
                else:
                    print("   ❌ Failed to send report")
            
            return {
                'success': True,
                'comparison_rows': comparison_rows,
                'totals': totals,
                'timestamp': datetime.now().isoformat()
            }
        else:
            print("\n⚠️  No comparison data available")
            return {'success': True, 'message': 'No comparison data available'}
    
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
            network_name_raw = row.get('network', '').upper().replace(' ', '_')
            network_key = self.NETWORK_NAME_MAP.get(network_name_raw)
            
            # Only include networks that have fetchers configured
            if not network_key or network_key not in network_data:
                continue
            
            # Apply include/exclude filters
            if include_networks and network_key not in include_networks:
                continue
            if network_key in exclude_networks:
                continue
            
            net_data = network_data[network_key]
            platform = 'ios' if 'iOS' in row.get('application', '') else 'android'
            ad_type = row.get('ad_type', '').lower()
            
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
    
    def _send_slack_report(self, comparison_rows: List[Dict], totals: Dict, start_date: datetime, end_date: datetime, network_data: Dict[str, Any] = None) -> bool:
        """Send Network Comparison report to Slack with separate blocks per network."""
        from datetime import timezone
        
        blocks = []
        
        # Header
        blocks.append({
            "type": "header",
            "text": {"type": "plain_text", "text": "📊 Network Comparison Report", "emoji": True}
        })
        
        # Generated date
        now_utc = datetime.now(timezone.utc)
        blocks.append({
            "type": "context",
            "elements": [{
                "type": "mrkdwn",
                "text": f"📅 *Generated:* {now_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC"
            }]
        })
        
        blocks.append({"type": "divider"})
        
        # Group rows by network
        networks = {}
        for row in comparison_rows:
            network_name = row['network']
            if network_name not in networks:
                networks[network_name] = []
            networks[network_name].append(row)
        
        # Network icons mapping
        network_icons = {
            'MINTEGRAL': '🟣',
            'MINTEGRAL_BIDDING': '🟣',
            'UNITY': '🎮',
            'UNITY_BIDDING': '🎮',
            'IRONSOURCE': '🟠',
            'IRONSOURCE_BIDDING': '🟠',
            'FACEBOOK': '🔵',
            'FACEBOOK_NETWORK': '🔵',
            'FACEBOOK_BIDDING': '🔵',
            'META': '🔵',
            'META_AUDIENCE_NETWORK': '🔵',
            'META_BIDDING': '🔵',
        }
        
        # Create separate block for each network
        for network_name, rows in networks.items():
            # Calculate network totals
            network_max_rev = sum(r['max_revenue'] for r in rows)
            network_net_rev = sum(r['network_revenue'] for r in rows)
            network_max_imps = sum(r['max_impressions'] for r in rows)
            network_net_imps = sum(r['network_impressions'] for r in rows)
            
            rev_delta = ((network_net_rev - network_max_rev) / network_max_rev * 100) if network_max_rev > 0 else 0
            imp_delta = ((network_net_imps - network_max_imps) / network_max_imps * 100) if network_max_imps > 0 else 0
            
            # Get network icon
            icon = network_icons.get(network_name.upper(), '📡')
            
            # Get network date range from network_data
            network_date_info = ""
            if network_data:
                # Map network display name to fetcher key
                network_key_raw = network_name.upper().replace(' ', '_')
                network_key = self.NETWORK_NAME_MAP.get(network_key_raw)
                if network_key and network_key in network_data:
                    net_date_range = network_data[network_key].get('date_range', {})
                    net_start = net_date_range.get('start', '')
                    net_end = net_date_range.get('end', '')
                    if net_start and net_end:
                        network_date_info = f"\n📅 Network Date: {net_start} to {net_end}"
            
            # Network section header
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{icon} *{network_name}*{network_date_info}\n💰 MAX: ${network_max_rev:,.2f} → Network: ${network_net_rev:,.2f} ({rev_delta:+.1f}%)\n📈 Imps: {network_max_imps:,} → {network_net_imps:,} ({imp_delta:+.1f}%)"
                }
            })
            
            # Build table for this network
            table_lines = []
            table_lines.append(f"{'Application':<28} │ {'Ad Type':<12} │ {'MAX Imps':>10} │ {'Net Imps':>10} │ {'Imp Δ':>8} │ {'MAX Rev':>10} │ {'Net Rev':>10} │ {'Rev Δ':>8} │ {'MAX CPM':>8} │ {'Net CPM':>8} │ {'CPM Δ':>8}")
            table_lines.append("─" * 155)
            
            for row in rows[:20]:  # Limit rows per network for Slack
                table_lines.append(
                    f"{row['application']:<28} │ "
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
            
            table_text = "\n".join(table_lines)
            
            # Use rich_text block with preformatted text for proper alignment
            blocks.append({
                "type": "rich_text",
                "elements": [
                    {
                        "type": "rich_text_preformatted",
                        "elements": [
                            {
                                "type": "text",
                                "text": table_text
                            }
                        ]
                    }
                ]
            })
            
            # Add divider between networks
            blocks.append({"type": "divider"})
        
        payload = {"blocks": blocks}
        if self.notifier.channel:
            payload["channel"] = self.notifier.channel
        
        return self.notifier._send_to_slack(payload)
    
    def test_slack_integration(self) -> bool:
        """Test Slack integration."""
        if not self.notifier:
            print("Slack notifier not configured")
            return False
        
        print("Sending test message to Slack...")
        success = self.notifier.send_test_message()
        print("✅ Test message sent" if success else "❌ Failed")
        return success

