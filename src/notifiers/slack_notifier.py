"""
Slack notifier for sending alerts.
"""
import requests
import json
from typing import Dict, List, Any
from datetime import datetime


class SlackNotifier:
    """Notifier for sending alerts to Slack."""
    
    # Ad type and platform order
    AD_TYPE_ORDER = ['banner', 'interstitial', 'rewarded']
    PLATFORM_ORDER = ['android', 'ios']
    
    def __init__(self, webhook_url: str, channel: str = None):
        """
        Initialize Slack notifier.
        
        Args:
            webhook_url: Slack webhook URL
            channel: Optional channel to post to (overrides webhook default)
        """
        self.webhook_url = webhook_url
        self.channel = channel
    
    def send_report(self, network_data: List[Dict[str, Any]], comparisons: List[Dict[str, Any]] = None) -> bool:
        """
        Send full report to Slack (same format as terminal output).
        
        Args:
            network_data: List of network data dictionaries
            comparisons: Optional list of comparison results
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        if not network_data:
            return False
        
        # Build message using terminal-style tables
        message = self._build_full_report(network_data, comparisons)
        
        # Send to Slack
        return self._send_to_slack(message)
    
    def send_discrepancy_alert(self, comparisons: List[Dict[str, Any]], network_data: List[Dict[str, Any]] = None) -> bool:
        """
        Send discrepancy alert to Slack.
        
        Args:
            comparisons: List of comparison results
            network_data: Optional network data for full report
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        # Filter only comparisons with discrepancies
        discrepancies = [comp for comp in comparisons if comp.get('has_discrepancy')]
        
        if not discrepancies:
            return True  # No discrepancies, nothing to send
        
        # If we have network_data, send full report
        if network_data:
            return self.send_report(network_data, comparisons)
        
        # Build message from comparisons only
        message = self._build_discrepancy_message(discrepancies)
        
        # Send to Slack
        return self._send_to_slack(message)
    
    def _build_full_report(self, network_data: List[Dict[str, Any]], comparisons: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Build full report message (compact summary only).
        """
        blocks = []
        
        # Get date range
        date_range = network_data[0].get('date_range', {})
        start_date = date_range.get('start', 'N/A')
        end_date = date_range.get('end', 'N/A')
        
        # Check for discrepancies
        has_discrepancy = any(comp.get('has_discrepancy') for comp in (comparisons or []))
        
        # Header
        header_emoji = "⚠️" if has_discrepancy else "📊"
        header_text = "Network Data Discrepancy Alert" if has_discrepancy else "Network Data Report"
        
        blocks.append({
            "type": "header",
            "text": {"type": "plain_text", "text": f"{header_emoji} {header_text}", "emoji": True}
        })
        
        blocks.append({
            "type": "context",
            "elements": [{
                "type": "mrkdwn",
                "text": f"📅 *Date:* {start_date} to {end_date} | 🕐 *Generated:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }]
        })
        
        blocks.append({"type": "divider"})
        
        # Network names
        network_names = [nd.get('network', 'Unknown') for nd in network_data]
        
        # Compact summary table only
        compact_table = self._generate_compact_table(network_data, network_names)
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"```{compact_table}```"}
        })
        
        # Discrepancy summary if any
        if has_discrepancy and comparisons:
            blocks.append({"type": "divider"})
            diff_summary = self._generate_diff_summary(comparisons)
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*⚠️ Discrepancy Details*\n{diff_summary}"}
            })
        
        payload = {"blocks": blocks}
        if self.channel:
            payload["channel"] = self.channel
        return payload
    
    def _generate_platform_table(self, platform: str, network_data: List[Dict[str, Any]], network_names: List[str]) -> str:
        """Generate platform table string."""
        lines = []
        
        # Header
        header = f"{'Ad Type':<14}"
        for name in network_names:
            header += f" | {'Revenue':>12} {'eCPM':>8} {'Impr':>10}"
        lines.append(header)
        
        # Network names row
        name_row = " " * 14
        for name in network_names:
            short_name = name[:12] if len(name) > 12 else name
            name_row += f" | {short_name:^32}"
        lines.append(name_row)
        lines.append("-" * len(header))
        
        # Collect all ad types
        all_ad_types = set()
        for nd in network_data:
            platform_info = nd.get('platform_data', {}).get(platform, {})
            all_ad_types.update(platform_info.get('ad_data', {}).keys())
        
        ordered_ad_types = [at for at in self.AD_TYPE_ORDER if at in all_ad_types]
        ordered_ad_types.extend([at for at in sorted(all_ad_types) if at not in self.AD_TYPE_ORDER])
        
        # Data rows
        for ad_type in ordered_ad_types:
            row = f"{ad_type.capitalize():<14}"
            for nd in network_data:
                platform_info = nd.get('platform_data', {}).get(platform, {})
                ad_info = platform_info.get('ad_data', {}).get(ad_type, {'revenue': 0, 'impressions': 0, 'ecpm': 0})
                
                rev = ad_info.get('revenue', 0)
                ecpm = ad_info.get('ecpm', 0)
                imp = ad_info.get('impressions', 0)
                
                row += f" | ${rev:>10,.0f} ${ecpm:>6.2f} {imp:>10,}"
            lines.append(row)
        
        # Total row
        lines.append("-" * len(header))
        total_row = f"{'TOTAL':<14}"
        for nd in network_data:
            platform_info = nd.get('platform_data', {}).get(platform, {'revenue': 0, 'impressions': 0, 'ecpm': 0})
            rev = platform_info.get('revenue', 0)
            ecpm = platform_info.get('ecpm', 0)
            imp = platform_info.get('impressions', 0)
            total_row += f" | ${rev:>10,.0f} ${ecpm:>6.2f} {imp:>10,}"
        lines.append(total_row)
        
        return "\n".join(lines)
    
    def _generate_compact_table(self, network_data: List[Dict[str, Any]], network_names: List[str]) -> str:
        """Generate compact table string with fixed-width columns for Slack."""
        lines = []
        
        # Simple fixed-width format for monospace display
        # Platform(12) | Network(14) | Rewarded(14) | Interstitial(14) | Banner(14) | Total(14)
        
        header = "Platform     | Network        | Rewarded       | Interstitial   | Banner         | Total"
        lines.append(header)
        lines.append("-" * 97)
        
        for platform in self.PLATFORM_ORDER:
            platform_icon = "🤖" if platform == "android" else "🍎"
            plat_name = "ANDROID" if platform == "android" else "IOS"
            
            for idx, nd in enumerate(network_data):
                network_name = nd.get('network', 'Unknown')
                # Truncate network name if too long
                short_name = network_name[:12] if len(network_name) > 12 else network_name
                platform_info = nd.get('platform_data', {}).get(platform, {})
                
                def format_cell(ad_type: str) -> str:
                    ad_info = platform_info.get('ad_data', {}).get(ad_type, {})
                    rev = ad_info.get('revenue', 0)
                    ecpm = ad_info.get('ecpm', 0)
                    return f"${rev:>6,.0f} ${ecpm:>5.2f}"
                
                total_rev = platform_info.get('revenue', 0)
                total_ecpm = platform_info.get('ecpm', 0)
                total_cell = f"${total_rev:>6,.0f} ${total_ecpm:>5.2f}"
                
                # First row shows platform, others are blank
                if idx == 0:
                    plat_col = f"{platform_icon} {plat_name:<8}"
                else:
                    plat_col = "            "
                
                row = f"{plat_col} | {short_name:<14} | {format_cell('rewarded')} | {format_cell('interstitial')} | {format_cell('banner')} | {total_cell}"
                lines.append(row)
            
            # Separator between platforms
            if platform != self.PLATFORM_ORDER[-1]:
                lines.append("-" * 97)
        
        return "\n".join(lines)
    
    def _generate_totals_text(self, network_data: List[Dict[str, Any]]) -> str:
        """Generate totals text."""
        lines = []
        
        baseline = network_data[0] if network_data else None
        
        for idx, nd in enumerate(network_data):
            name = nd.get('network', 'Unknown')
            revenue = nd.get('revenue', 0)
            impressions = nd.get('impressions', 0)
            ecpm = nd.get('ecpm', 0)
            
            diff_str = ""
            if idx > 0 and baseline:
                base_rev = baseline.get('revenue', 0)
                if base_rev > 0:
                    diff_pct = ((revenue - base_rev) / base_rev) * 100
                    sign = "+" if diff_pct > 0 else ""
                    diff_str = f" ({sign}{diff_pct:.1f}%)"
            
            line = f"{name:<20} ${revenue:>12,.2f}{diff_str:<12} ${ecpm:>6.2f}  {impressions:>12,}"
            lines.append(line)
        
        return "\n".join(lines)
    
    def _generate_diff_summary(self, comparisons: List[Dict[str, Any]]) -> str:
        """Generate discrepancy summary text."""
        lines = []
        
        for comp in comparisons:
            if not comp.get('has_discrepancy'):
                continue
            
            network1 = comp.get('network1', 'Unknown')
            network2 = comp.get('network2', 'Unknown')
            
            lines.append(f"*{network1} vs {network2}*")
            
            # Overall metrics
            for disc in comp.get('discrepancies', []):
                if disc.get('over_threshold'):
                    metric = disc['metric'].upper()
                    v1 = disc['network1_value']
                    v2 = disc['network2_value']
                    pct = disc['difference_percentage']
                    pct_str = "∞" if pct == float('inf') else f"{pct:.1f}%"
                    
                    if metric == 'REVENUE':
                        lines.append(f"  💰 {metric}: ${v1:,.2f} → ${v2:,.2f} (`{pct_str}`)")
                    elif metric == 'ECPM':
                        lines.append(f"  📊 {metric}: ${v1:.2f} → ${v2:.2f} (`{pct_str}`)")
                    else:
                        lines.append(f"  📈 {metric}: {v1:,} → {v2:,} (`{pct_str}`)")
            
            # Platform-level
            plat_comp = comp.get('platform_comparison', {})
            if plat_comp.get('has_discrepancy'):
                for plat, plat_info in plat_comp.get('platforms', {}).items():
                    plat_icon = "🤖" if plat == "android" else "🍎"
                    
                    for ad_type, ad_info in plat_info.get('ad_types', {}).items():
                        if ad_info.get('revenue_over_threshold'):
                            pct = ad_info['revenue_diff_pct']
                            pct_str = "∞" if pct == float('inf') else f"{pct:.1f}%"
                            n1 = ad_info.get('network1', {})
                            n2 = ad_info.get('network2', {})
                            lines.append(
                                f"  {plat_icon} {plat.upper()} {ad_type.capitalize()}: "
                                f"${n1.get('revenue', 0):,.2f} → ${n2.get('revenue', 0):,.2f} (`{pct_str}`)"
                            )
        
        return "\n".join(lines) if lines else "No significant discrepancies."
    
    def _build_discrepancy_message(self, discrepancies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build discrepancy-only message (fallback when no network_data)."""
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "⚠️ Network Data Discrepancy Alert", "emoji": True}
            },
            {
                "type": "context",
                "elements": [{
                    "type": "mrkdwn",
                    "text": f"📅 *Date:* {discrepancies[0]['date_range']['start']} to {discrepancies[0]['date_range']['end']} | 🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }]
            },
            {"type": "divider"}
        ]
        
        diff_summary = self._generate_diff_summary(discrepancies)
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": diff_summary}
        })
        
        payload = {"blocks": blocks}
        if self.channel:
            payload["channel"] = self.channel
        return payload
    
    def _send_to_slack(self, payload: Dict[str, Any]) -> bool:
        """
        Send payload to Slack webhook.
        
        Args:
            payload: Message payload
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            response = requests.post(
                self.webhook_url,
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Failed to send Slack notification: {str(e)}")
            return False
    
    def send_test_message(self) -> bool:
        """
        Send a test message to verify Slack integration.
        
        Returns:
            True if sent successfully, False otherwise
        """
        payload = {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "✅ *Test Message*\n\nNetwork Data Validation System is configured and running!"
                    }
                }
            ]
        }
        
        if self.channel:
            payload["channel"] = self.channel
        
        return self._send_to_slack(payload)
