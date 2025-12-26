"""
Main validation service orchestrating data fetching, validation, and notifications.
Compares Applovin Max network breakdown data against each network's own API data.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any
from src.config import Config
from src.fetchers import AdjustFetcher, ApplovinFetcher, MockAdjustFetcher, MintegralFetcher, MockMintegralFetcher, NetworkDataFetcher
from src.validators import DataValidator
from src.notifiers import SlackNotifier
from src.reporters import TableReporter


class ValidationService:
    """Main service for orchestrating network data validation."""
    
    # Mapping from fetcher network names to Applovin breakdown names
    NETWORK_NAME_MAP = {
        'Adjust': ['Adjust'],
        'Adjust (Mock)': ['Adjust'],
        'Mintegral': ['Mintegral'],
        'AdMob': ['Admob', 'AdMob', 'ADMOB'],
        'Meta': ['Facebook', 'Meta', 'META_AUDIENCE_NETWORK'],
        'Unity Ads': ['Unity', 'Unity Ads', 'UNITY'],
        'IronSource': ['Ironsource', 'IronSource', 'IRONSOURCE'],
        'Vungle': ['Vungle', 'VUNGLE'],
        'Pangle': ['Tiktok', 'Pangle', 'Bytedance', 'PANGLE'],
        'Chartboost': ['Chartboost', 'CHARTBOOST'],
        'InMobi': ['Inmobi', 'InMobi', 'INMOBI'],
        'AppLovin': ['Applovin', 'AppLovin', 'APPLOVIN'],
    }
    
    def __init__(self, config: Config):
        """Initialize validation service."""
        self.config = config
        self.applovin_fetcher = None
        self.network_fetchers: List[NetworkDataFetcher] = []
        self.validator = None
        self.notifier = None
        self.reporter = TableReporter()
        
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize fetchers, validator, and notifier based on configuration."""
        # Initialize Applovin Max fetcher (baseline/reference)
        applovin_config = self.config.get_applovin_config()
        if applovin_config and applovin_config.get('api_key') and applovin_config.get('package_name'):
            self.applovin_fetcher = ApplovinFetcher(
                api_key=applovin_config['api_key'],
                package_name=applovin_config['package_name']
            )
        
        # Add other networks to compare against Applovin's breakdown
        adjust_config = self.config.get_adjust_config()
        if adjust_config and adjust_config.get('api_token') and adjust_config.get('app_token'):
            use_mock = adjust_config.get('use_mock', False)
            if use_mock:
                self.network_fetchers.append(MockAdjustFetcher())
            else:
                self.network_fetchers.append(
                    AdjustFetcher(
                        api_token=adjust_config['api_token'],
                        app_token=adjust_config['app_token']
                    )
                )
        
        # Add Mintegral
        mintegral_config = self.config.get_mintegral_config()
        if mintegral_config and mintegral_config.get('skey') and mintegral_config.get('secret'):
            use_mock = mintegral_config.get('use_mock', False)
            if use_mock:
                self.network_fetchers.append(MockMintegralFetcher())
            else:
                self.network_fetchers.append(
                    MintegralFetcher(
                        skey=mintegral_config['skey'],
                        secret=mintegral_config['secret'],
                        app_id=mintegral_config.get('app_id')
                    )
                )
        
        # Initialize validator
        validation_config = self.config.get_validation_config()
        threshold = validation_config.get('threshold_percentage', 5.0)
        self.validator = DataValidator(threshold_percentage=threshold)
        
        # Initialize notifier
        slack_config = self.config.get_slack_config()
        if slack_config and slack_config.get('webhook_url'):
            self.notifier = SlackNotifier(
                webhook_url=slack_config['webhook_url'],
                channel=slack_config.get('channel')
            )
    
    def _find_applovin_network_data(self, network_breakdown: Dict, network_name: str) -> Dict[str, Any]:
        """Find matching network data from Applovin breakdown."""
        possible_names = self.NETWORK_NAME_MAP.get(network_name, [network_name])
        
        # Direct match
        for name in possible_names:
            if name in network_breakdown:
                return network_breakdown[name]
        
        # Match with suffix variations (Bidding, Network, Exchange)
        for key in network_breakdown:
            key_base = key.replace(' Bidding', '').replace(' Network', '').replace(' Exchange', '').strip()
            
            # Check against possible names
            for pn in possible_names:
                if key_base.lower() == pn.lower():
                    return network_breakdown[key]
            
            # Check against network_name directly
            if key_base.lower() == network_name.lower().replace(' (mock)', '').strip():
                return network_breakdown[key]
        
        # Partial match (network name contained in key)
        for key in network_breakdown:
            for pn in possible_names:
                if pn.lower() in key.lower():
                    return network_breakdown[key]
        
        return None
    
    def run_validation(self) -> Dict[str, Any]:
        """
        Run validation check comparing Applovin network breakdown vs each network's own API.
        """
        print(f"[{datetime.now()}] Starting validation check...")
        print("=" * 80)
        
        # Calculate date range
        validation_config = self.config.get_validation_config()
        date_range_days = validation_config.get('date_range_days', 1)
        end_date = datetime.now() - timedelta(days=1)
        start_date = end_date - timedelta(days=date_range_days - 1)
        
        print(f"📅 Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print("=" * 80)
        
        # Fetch Applovin Max data (with network breakdown)
        applovin_data = None
        if self.applovin_fetcher:
            try:
                print(f"\n📊 Fetching data from Applovin Max (Reference)...")
                applovin_data = self.applovin_fetcher.fetch_data(start_date, end_date)
                print(f"   Total: ${applovin_data['revenue']:,.2f} | {applovin_data['impressions']:,} imp | ${applovin_data['ecpm']:.2f} eCPM")
                
                # Show network breakdown
                network_breakdown = applovin_data.get('network_breakdown', {})
                if network_breakdown:
                    print(f"\n   📈 Network Breakdown (as seen in Applovin Max):")
                    for net_name, net_data in sorted(network_breakdown.items()):
                        print(f"      {net_name:<15}: ${net_data['revenue']:>10,.2f} | {net_data['impressions']:>10,} imp | ${net_data['ecpm']:>6.2f} eCPM")
                else:
                    print("   ⚠️  No network breakdown available from Applovin")
            except Exception as e:
                print(f"   ❌ Error fetching Applovin data: {str(e)}")
                return {'success': False, 'message': f'Failed to fetch Applovin data: {str(e)}'}
        else:
            print("❌ Applovin fetcher not configured")
            return {'success': False, 'message': 'Applovin fetcher not configured'}
        
        # Fetch data from each network's own API
        print(f"\n{'=' * 80}")
        print("📊 Fetching data from individual network APIs...")
        print("=" * 80)
        
        network_own_data = {}
        for fetcher in self.network_fetchers:
            try:
                network_name = fetcher.get_network_name()
                print(f"\n   🔄 Fetching from {network_name}...")
                data = fetcher.fetch_data(start_date, end_date)
                network_own_data[network_name] = data
                print(f"      Total: ${data['revenue']:,.2f} | {data['impressions']:,} imp | ${data['ecpm']:.2f} eCPM")
            except Exception as e:
                print(f"      ❌ Error: {str(e)}")
        
        # Build comparison data for table display
        comparison_rows = []
        network_breakdown = applovin_data.get('network_breakdown', {})
        
        print(f"\n{'=' * 80}")
        print("📊 COMPARISON: Applovin Max Data vs Network's Own API Data")
        print("=" * 80)
        
        for network_name, own_data in network_own_data.items():
            applovin_network_data = self._find_applovin_network_data(network_breakdown, network_name)
            
            if applovin_network_data:
                comparison_rows.append({
                    'network': network_name,
                    'applovin_data': applovin_network_data,
                    'own_data': own_data
                })
            else:
                print(f"\n   ⚠️  {network_name}: Not found in Applovin breakdown")
                comparison_rows.append({
                    'network': network_name,
                    'applovin_data': None,
                    'own_data': own_data
                })
        
        # Generate comparison table
        if comparison_rows:
            table = self._generate_comparison_table(comparison_rows, start_date, end_date)
            print(table)
            
            # Check for discrepancies
            discrepancies = self._check_discrepancies(comparison_rows)
            
            # Send to Slack
            if self.notifier:
                print("\n📤 Sending report to Slack...")
                success = self._send_slack_report(comparison_rows, discrepancies, start_date, end_date)
                if success:
                    print("   ✅ Report sent successfully")
                else:
                    print("   ❌ Failed to send report")
            
            return {
                'success': True,
                'has_discrepancy': len(discrepancies) > 0,
                'discrepancies': discrepancies,
                'comparison_rows': comparison_rows,
                'timestamp': datetime.now().isoformat()
            }
        else:
            print("\n⚠️  No networks to compare")
            return {
                'success': True,
                'has_discrepancy': False,
                'message': 'No networks to compare',
                'timestamp': datetime.now().isoformat()
            }
    
    def _generate_comparison_table(self, comparison_rows: List[Dict], start_date: datetime, end_date: datetime) -> str:
        """Generate comparison table showing Applovin data vs Network's own data per platform."""
        lines = []
        
        for row in comparison_rows:
            network = row['network']
            applovin_data = row.get('applovin_data')
            own_data = row.get('own_data')
            
            if not applovin_data and not own_data:
                continue
            
            for platform in ['android', 'ios']:
                platform_icon = "🤖" if platform == "android" else "🍎"
                plat_name = "ANDROID" if platform == "android" else "IOS"
                
                ap_plat = applovin_data.get('platform_data', {}).get(platform, {}) if applovin_data else {}
                own_plat = own_data.get('platform_data', {}).get(platform, {}) if own_data else {}
                
                lines.append("")
                lines.append(f"{platform_icon} {plat_name} Platform")
                lines.append(f"                  │               Applovin Max                  │               {network[:18]:<18}         ")
                lines.append(f"Ad Type           │    Revenue     │     eCPM     │     Impr     │    Revenue     │     eCPM     │     Impr")
                lines.append(f"──────────────────┼────────────────┼──────────────┼──────────────┼────────────────┼──────────────┼──────────────")
                
                for ad_type in ['Banner', 'Interstitial', 'Rewarded']:
                    ad_key = ad_type.lower()
                    ap_ad = ap_plat.get('ad_data', {}).get(ad_key, {'revenue': 0, 'ecpm': 0, 'impressions': 0})
                    own_ad = own_plat.get('ad_data', {}).get(ad_key, {'revenue': 0, 'ecpm': 0, 'impressions': 0})
                    
                    lines.append(
                        f"{ad_type:<17} │ "
                        f"${ap_ad.get('revenue',0):>12,.2f}  │  ${ap_ad.get('ecpm',0):>8.2f}  │  {ap_ad.get('impressions',0):>10,}  │ "
                        f"${own_ad.get('revenue',0):>12,.2f}  │  ${own_ad.get('ecpm',0):>8.2f}  │  {own_ad.get('impressions',0):>10,}"
                    )
                
                lines.append(f"──────────────────┼────────────────┼──────────────┼──────────────┼────────────────┼──────────────┼──────────────")
                
                lines.append(
                    f"{'TOTAL':<17} │ "
                    f"${ap_plat.get('revenue',0):>12,.2f}  │  ${ap_plat.get('ecpm',0):>8.2f}  │  {ap_plat.get('impressions',0):>10,}  │ "
                    f"${own_plat.get('revenue',0):>12,.2f}  │  ${own_plat.get('ecpm',0):>8.2f}  │  {own_plat.get('impressions',0):>10,}"
                )
                
                # Diff
                ap_tr = ap_plat.get('revenue', 0)
                own_tr = own_plat.get('revenue', 0)
                if ap_tr == 0 and own_tr == 0:
                    diff_str = "-"
                elif ap_tr == 0:
                    diff_str = "∞%"
                else:
                    diff = ((own_tr - ap_tr) / ap_tr) * 100
                    sign = "+" if diff > 0 else ""
                    diff_str = f"{sign}{diff:.1f}%"
                
                lines.append(f"{'DIFF':<17} │ Revenue: {diff_str}")
                lines.append("")
        
        return "\n".join(lines)
    
    def _calc_diff(self, applovin_val: float, own_val: float) -> str:
        """Calculate difference percentage."""
        if applovin_val == 0 and own_val == 0:
            return "-"
        elif applovin_val == 0:
            return "∞%"
        diff_pct = ((own_val - applovin_val) / applovin_val) * 100
        sign = "+" if diff_pct > 0 else ""
        return f"Revenue: {sign}{diff_pct:.1f}%"
    
    def _format_table_row(self, platform: str, network: str, source: str, plat_data: Dict) -> str:
        """Format a single table row."""
        def get_cell(ad_type: str) -> str:
            ad_info = plat_data.get('ad_data', {}).get(ad_type, {})
            rev = ad_info.get('revenue', 0)
            return f"${rev:,.0f}"
        
        total = plat_data.get('revenue', 0)
        
        return f"│ {platform:<10} │ {network:<13} │ {source:<10} │ {get_cell('rewarded'):>12} │ {get_cell('interstitial'):>12} │ {get_cell('banner'):>12} │ ${total:>10,.0f} │"
    
    def _format_diff_row(self, applovin_plat: Dict, own_plat: Dict) -> str:
        """Format difference row."""
        def get_diff(ad_type: str) -> str:
            applovin_rev = applovin_plat.get('ad_data', {}).get(ad_type, {}).get('revenue', 0)
            own_rev = own_plat.get('ad_data', {}).get(ad_type, {}).get('revenue', 0)
            
            if applovin_rev == 0 and own_rev == 0:
                return "-"
            elif applovin_rev == 0:
                return "∞%"
            diff_pct = ((own_rev - applovin_rev) / applovin_rev) * 100
            sign = "+" if diff_pct > 0 else ""
            return f"{sign}{diff_pct:.1f}%"
        
        applovin_total = applovin_plat.get('revenue', 0)
        own_total = own_plat.get('revenue', 0)
        
        if applovin_total == 0 and own_total == 0:
            total_diff = "-"
        elif applovin_total == 0:
            total_diff = "∞%"
        else:
            diff_pct = ((own_total - applovin_total) / applovin_total) * 100
            sign = "+" if diff_pct > 0 else ""
            total_diff = f"{sign}{diff_pct:.1f}%"
        
        return f"│ {'':10} │ {'':13} │ {'DIFF':<10} │ {get_diff('rewarded'):>12} │ {get_diff('interstitial'):>12} │ {get_diff('banner'):>12} │ {total_diff:>11} │"
    
    def _check_discrepancies(self, comparison_rows: List[Dict]) -> List[Dict]:
        """Check for discrepancies exceeding threshold."""
        discrepancies = []
        threshold = self.validator.threshold_percentage
        
        for row in comparison_rows:
            applovin_data = row.get('applovin_data')
            own_data = row.get('own_data')
            
            if not applovin_data or not own_data:
                continue
            
            for platform in ['android', 'ios']:
                applovin_plat = applovin_data.get('platform_data', {}).get(platform, {})
                own_plat = own_data.get('platform_data', {}).get(platform, {})
                
                for ad_type in ['rewarded', 'interstitial', 'banner']:
                    applovin_rev = applovin_plat.get('ad_data', {}).get(ad_type, {}).get('revenue', 0)
                    own_rev = own_plat.get('ad_data', {}).get(ad_type, {}).get('revenue', 0)
                    
                    if applovin_rev == 0 and own_rev == 0:
                        continue
                    
                    if applovin_rev == 0:
                        diff_pct = float('inf')
                    else:
                        diff_pct = abs((own_rev - applovin_rev) / applovin_rev) * 100
                    
                    if diff_pct > threshold:
                        discrepancies.append({
                            'network': row['network'],
                            'platform': platform,
                            'ad_type': ad_type,
                            'applovin_revenue': applovin_rev,
                            'own_revenue': own_rev,
                            'diff_percentage': diff_pct
                        })
        
        return discrepancies
    
    def _send_slack_report(self, comparison_rows: List[Dict], discrepancies: List[Dict], start_date: datetime, end_date: datetime) -> bool:
        """Send comparison report to Slack."""
        blocks = []
        
        # Header
        has_disc = len(discrepancies) > 0
        header_emoji = "⚠️" if has_disc else "📊"
        header_text = "Network Data Discrepancy Alert" if has_disc else "Network Data Report"
        
        blocks.append({
            "type": "header",
            "text": {"type": "plain_text", "text": f"{header_emoji} {header_text}", "emoji": True}
        })
        
        blocks.append({
            "type": "context",
            "elements": [{
                "type": "mrkdwn",
                "text": f"📅 *Date:* {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} | 🕐 *Generated:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }]
        })
        
        blocks.append({"type": "divider"})
        
        # Comparison tables per network per platform - using rich_text block
        for row in comparison_rows:
            network = row['network']
            applovin_data = row.get('applovin_data')
            own_data = row.get('own_data')
            
            if not applovin_data and not own_data:
                continue
            
            for platform in ['android', 'ios']:
                plat_icon = "🤖" if platform == "android" else "🍎"
                plat_name = "ANDROID" if platform == "android" else "IOS"
                
                ap_plat = applovin_data.get('platform_data', {}).get(platform, {}) if applovin_data else {}
                own_plat = own_data.get('platform_data', {}).get(platform, {}) if own_data else {}
                
                net_short = network[:15]
                
                # Helper function for diff calculation
                def calc_diff_str(ap_val, own_val):
                    if ap_val == 0 and own_val == 0:
                        return "-"
                    elif ap_val == 0:
                        return "∞%"
                    else:
                        diff = ((own_val - ap_val) / ap_val) * 100
                        sign = "+" if diff > 0 else ""
                        return f"{sign}{diff:.1f}%"
                
                # Fixed column widths - precisely matched
                W_AD = 15    # width for ad type
                W_REV = 15    # width for revenue value after $
                W_ECPM = 15   # width for ecpm value after $
                W_IMPR = 15   # width for impr value
                W_DREV = 15  # width for diff revenue percentage
                W_DECPM = 15  # width for diff ecpm percentage
                W_DIMPR = 15  # width for diff impr percentage
                
                # Header separator widths (content + 2 spaces)
                SEP_REV = '-' * (W_REV + 3)    # 11 dashes
                SEP_ECPM = '-' * (W_ECPM + 3)  # 7 dashes
                SEP_IMPR = '-' * (W_IMPR + 2)  # 11 dashes
                SEP_DREV = '-' * (W_DREV + 2)  # 13 dashes
                SEP_DECPM = '-' * (W_DECPM + 2) # 9 dashes
                SEP_DIMPR = '-' * (W_DIMPR + 2) # 11 dashes
                SEP_AD = '-' * (W_AD + 2)      # 17 dashes
                
                table_lines = []
                table_lines.append(f"{plat_icon} {plat_name} Platform")
                table_lines.append(f"")
                table_lines.append(f"| {'Ad Type':<{W_AD}} |{'Applovin Max':^{W_REV+W_ECPM+W_IMPR+10}}|{net_short:^{W_REV+W_ECPM+W_IMPR+10}}|{'DIFF':^{W_DREV+W_DECPM+W_DIMPR+8}}|")
                table_lines.append(f"|{SEP_AD+SEP_REV+SEP_ECPM+SEP_IMPR+SEP_REV+SEP_ECPM+SEP_IMPR+SEP_DREV+SEP_DECPM+SEP_DIMPR+('-'*9)}|")
                table_lines.append(f"| {'':<{W_AD}} | {'Revenue':<{W_REV+1}} | {'eCPM':<{W_ECPM+1}} | {'Impr':<{W_IMPR}} | {'Revenue':<{W_REV+1}} | {'eCPM':<{W_ECPM+1}} | {'Impr':<{W_IMPR}} | {'Revenue':<{W_DREV}} | {'eCPM':<{W_DECPM}} | {'Impr':<{W_DIMPR}} |")
                table_lines.append(f"|{SEP_AD}|{SEP_REV}|{SEP_ECPM}|{SEP_IMPR}|{SEP_REV}|{SEP_ECPM}|{SEP_IMPR}|{SEP_DREV}|{SEP_DECPM}|{SEP_DIMPR}|")
                
                for ad_type in ['Banner', 'Interstitial', 'Rewarded']:
                    ad_key = ad_type.lower()
                    ap_ad = ap_plat.get('ad_data', {}).get(ad_key, {'revenue': 0, 'ecpm': 0, 'impressions': 0})
                    own_ad = own_plat.get('ad_data', {}).get(ad_key, {'revenue': 0, 'ecpm': 0, 'impressions': 0})
                    
                    # Calculate diffs for this ad type
                    rev_diff = calc_diff_str(ap_ad.get('revenue', 0), own_ad.get('revenue', 0))
                    ecpm_diff = calc_diff_str(ap_ad.get('ecpm', 0), own_ad.get('ecpm', 0))
                    impr_diff = calc_diff_str(ap_ad.get('impressions', 0), own_ad.get('impressions', 0))
                    
                    table_lines.append(
                        f"| {ad_type:<{W_AD}} "
                        f"| ${ap_ad.get('revenue',0):>{W_REV},.2f} | ${ap_ad.get('ecpm',0):>{W_ECPM}.2f} | {ap_ad.get('impressions',0):>{W_IMPR},} "
                        f"| ${own_ad.get('revenue',0):>{W_REV},.2f} | ${own_ad.get('ecpm',0):>{W_ECPM}.2f} | {own_ad.get('impressions',0):>{W_IMPR},} "
                        f"| {rev_diff:>{W_DREV}} | {ecpm_diff:>{W_DECPM}} | {impr_diff:>{W_DIMPR}} |"
                    )
                
                table_lines.append(f"|{SEP_AD}|{SEP_REV}|{SEP_ECPM}|{SEP_IMPR}|{SEP_REV}|{SEP_ECPM}|{SEP_IMPR}|{SEP_DREV}|{SEP_DECPM}|{SEP_DIMPR}|")
                
                # Calculate total diffs
                ap_rev = ap_plat.get('revenue', 0)
                own_rev = own_plat.get('revenue', 0)
                ap_ecpm = ap_plat.get('ecpm', 0)
                own_ecpm = own_plat.get('ecpm', 0)
                ap_impr = ap_plat.get('impressions', 0)
                own_impr = own_plat.get('impressions', 0)
                
                total_rev_diff = calc_diff_str(ap_rev, own_rev)
                total_ecpm_diff = calc_diff_str(ap_ecpm, own_ecpm)
                total_impr_diff = calc_diff_str(ap_impr, own_impr)
                
                table_lines.append(
                    f"| {'TOTAL':<{W_AD}} "
                    f"| ${ap_plat.get('revenue',0):>{W_REV},.2f} | ${ap_plat.get('ecpm',0):>{W_ECPM},.2f} | {ap_plat.get('impressions',0):>{W_IMPR},} "
                    f"| ${own_plat.get('revenue',0):>{W_REV},.2f} | ${own_plat.get('ecpm',0):>{W_ECPM},.2f} | {own_plat.get('impressions',0):>{W_IMPR},} "
                    f"| {total_rev_diff:>{W_DREV}} | {total_ecpm_diff:>{W_DECPM}} | {total_impr_diff:>{W_DIMPR}} |"
                )
                
                table_text = "\n".join(table_lines)
                
                # Use rich_text block with preformatted text
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
            
            blocks.append({"type": "divider"})
        
        payload = {"blocks": blocks}
        if self.notifier.channel:
            payload["channel"] = self.notifier.channel
        
        return self.notifier._send_to_slack(payload)
    
    def test_slack_integration(self) -> bool:
        """Test Slack integration by sending a test message."""
        if not self.notifier:
            print("Slack notifier not configured")
            return False
        
        print("Sending test message to Slack...")
        success = self.notifier.send_test_message()
        
        if success:
            print("✅ Test message sent successfully")
        else:
            print("❌ Failed to send test message")
        
        return success
