"""
Slack notifier for sending alerts.
"""
import requests
import json
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timezone

from src.enums import NetworkName
from src.utils import parse_delta_percentage


class SlackNotifier:
    """Notifier for sending alerts to Slack."""
    
    # Ad type and platform order
    AD_TYPE_ORDER = ['banner', 'interstitial', 'rewarded']
    PLATFORM_ORDER = ['android', 'ios']
    
    # Legacy icon mapping (fallback for unknown network names)
    # Prefer using NetworkName.icon property instead
    NETWORK_ICONS = {
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
        'PANGLE': '🎯',
        'PANGLE_BIDDING': '🎯',
        'TIKTOK': '🎯',
        'TIKTOK_BIDDING': '🎯',
        'GOOGLE': '🔴',
        'GOOGLE_BIDDING': '🔴',
        'ADMOB': '🔴',
        'ADMOB_BIDDING': '🔴',
        'APPLOVIN': '🟢',
        'APPLOVIN_BIDDING': '🟢',
        'LIFTOFF': '🚀',
        'LIFTOFF_BIDDING': '🚀',
        'VUNGLE': '🚀',
        'VUNGLE_BIDDING': '🚀',
        'DT_EXCHANGE': '💠',
        'DT_EXCHANGE_BIDDING': '💠',
        'FYBER': '💠',
        'FYBER_BIDDING': '💠',
        'BIDMACHINE': '⚙️',
        'BIDMACHINE_BIDDING': '⚙️',
        'INMOBI': '🟡',
        'INMOBI_BIDDING': '🟡',
        'MOLOCO': '🔶',
        'MOLOCO_BIDDING': '🔶',
    }
    
    def __init__(self, webhook_url: str, channel: str = None):
        """
        Initialize Slack notifier.
        
        Args:
            webhook_url: Slack webhook URL
            channel: Optional channel to post to (overrides webhook default)
        """
        self.webhook_url = webhook_url
        self.channel = channel
    
    def send_comparison_report(
        self,
        comparison_rows: List[Dict],
        totals: Dict,
        end_date: datetime,
        network_data: Dict[str, Any] = None,
        threshold: float = 10.0,
        min_revenue: float = 25.0,
        network_key_resolver: Callable[[str], Optional[str]] = None
    ) -> bool:
        """
        Send Network Comparison report to Slack with separate blocks per network.
        
        Only shows app/ad_type rows where |rev_delta| > threshold.
        If all rows are below threshold, sends a summary "all normal" message.
        
        Args:
            comparison_rows: List of comparison row dictionaries
            totals: Dictionary with total values
            end_date: Report end date
            network_data: Optional dictionary with network fetch results
            threshold: Revenue delta threshold percentage (default 10%)
            min_revenue: Minimum revenue to check threshold (default $25)
            network_key_resolver: Optional function to resolve network display name to fetcher key
            
        Returns:
            True if sent successfully, False otherwise
        """
        # Filter rows by revenue delta threshold AND minimum revenue
        total_rows = len(comparison_rows)
        filtered_rows = []
        low_revenue_rows = 0
        
        for row in comparison_rows:
            max_rev = row.get('max_revenue', 0)
            
            # Skip rows with revenue below minimum threshold
            if max_rev < min_revenue:
                low_revenue_rows += 1
                continue
            
            rev_delta_value = parse_delta_percentage(row.get('rev_delta', '0%'))
            if abs(rev_delta_value) > threshold:
                filtered_rows.append(row)
        
        filtered_count = len(filtered_rows)
        checked_rows = total_rows - low_revenue_rows
        
        # Check for failed networks
        failed_networks = network_data.get('_failed_networks', []) if network_data else []
        
        blocks = []
        now_utc = datetime.now(timezone.utc)
        
        # If no rows exceed threshold, send "all normal" message
        if not filtered_rows:
            blocks = self._build_all_normal_blocks(
                totals, end_date, now_utc, threshold, min_revenue,
                total_rows, checked_rows, low_revenue_rows, failed_networks
            )
        else:
            blocks = self._build_threshold_exceeded_blocks(
                comparison_rows, filtered_rows, totals, end_date, now_utc,
                threshold, min_revenue, total_rows, checked_rows, low_revenue_rows,
                filtered_count, failed_networks, network_data, network_key_resolver
            )
        
        payload = {"blocks": blocks}
        if self.channel:
            payload["channel"] = self.channel
        
        return self._send_to_slack(payload)

    def send_multi_day_comparison_report(
        self,
        comparison_rows: List[Dict],
        network_data: Dict[str, Any] = None,
        threshold: float = 10.0,
        min_revenue: float = 25.0,
        network_key_resolver: Callable[[str], Optional[str]] = None
    ) -> bool:
        """
        Send 7-day aggregated Network Comparison report to Slack.
        
        Aggregates data across all dates and shows summary by network with date range.
        
        Args:
            comparison_rows: List of comparison row dictionaries (with 'date' field)
            network_data: Optional dictionary with network fetch results
            threshold: Revenue delta threshold percentage (default 10%)
            min_revenue: Minimum revenue to check threshold (default $25)
            network_key_resolver: Optional function to resolve network display name to fetcher key
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not comparison_rows:
            return False
        
        # Get date range from comparison rows
        dates = sorted(set(row.get('date', '') for row in comparison_rows if row.get('date')))
        if not dates:
            # Fallback to single-day report
            return self.send_comparison_report(
                comparison_rows, 
                self._calculate_totals_from_rows(comparison_rows),
                datetime.now(),
                network_data, threshold, min_revenue, network_key_resolver
            )
        
        date_start = dates[0]
        date_end = dates[-1]
        num_days = len(dates)
        
        # Calculate aggregated totals by network
        network_totals = {}
        for row in comparison_rows:
            network = row.get('network', 'Unknown')
            if network not in network_totals:
                network_totals[network] = {
                    'max_revenue': 0, 'network_revenue': 0,
                    'max_impressions': 0, 'network_impressions': 0,
                    'dates': set(), 'rows': [],
                    'filtered_rows': []  # Rows exceeding threshold
                }
            
            network_totals[network]['max_revenue'] += row.get('max_revenue', 0)
            network_totals[network]['network_revenue'] += row.get('network_revenue', 0)
            network_totals[network]['max_impressions'] += row.get('max_impressions', 0)
            network_totals[network]['network_impressions'] += row.get('network_impressions', 0)
            network_totals[network]['dates'].add(row.get('date', ''))
            network_totals[network]['rows'].append(row)
            
            # Check if this row exceeds threshold
            max_rev = row.get('max_revenue', 0)
            if max_rev >= min_revenue:
                rev_delta_value = parse_delta_percentage(row.get('rev_delta', '0%'))
                if abs(rev_delta_value) > threshold:
                    network_totals[network]['filtered_rows'].append(row)
        
        # Calculate overall totals
        overall_max_rev = sum(n['max_revenue'] for n in network_totals.values())
        overall_net_rev = sum(n['network_revenue'] for n in network_totals.values())
        overall_max_imps = sum(n['max_impressions'] for n in network_totals.values())
        overall_net_imps = sum(n['network_impressions'] for n in network_totals.values())
        
        overall_rev_delta = ((overall_net_rev - overall_max_rev) / overall_max_rev * 100) if overall_max_rev > 0 else 0
        overall_imp_delta = ((overall_net_imps - overall_max_imps) / overall_max_imps * 100) if overall_max_imps > 0 else 0
        
        # Check for failed networks
        failed_networks = network_data.get('_failed_networks', []) if network_data else []
        
        # Count rows exceeding threshold
        total_filtered = sum(len(n['filtered_rows']) for n in network_totals.values())
        total_rows = len(comparison_rows)
        
        blocks = []
        now_utc = datetime.now(timezone.utc)
        
        # Header based on whether threshold was exceeded
        if total_filtered > 0 or failed_networks:
            header_text = "⚠️ 7-Day Network Comparison - Threshold Aşıldı" if total_filtered > 0 else "⚠️ 7-Day Network Comparison - Eksik Veri"
        else:
            header_text = "✅ 7-Day Network Comparison - All Normal"
        
        blocks.append({
            "type": "header",
            "text": {"type": "plain_text", "text": header_text, "emoji": True}
        })
        
        # Context with date range and summary
        context_msg = f"📅 *Date Range:* {date_start} → {date_end} ({num_days} days) | "
        context_msg += f"📅 *Generated:* {now_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC"
        
        if total_filtered > 0:
            context_msg += f" | ⚠️ *{total_filtered}/{total_rows}* satır threshold (±{threshold}%) aştı"
        
        if failed_networks:
            context_msg += f" | 🚨 *Eksik:* {', '.join(failed_networks)}"
        
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": context_msg}]
        })
        
        blocks.append({"type": "divider"})
        
        # Overall summary
        summary_msg = f"*📊 7-Gün Toplam ({num_days} gün)*\n"
        summary_msg += f"💰 Revenue: MAX ${overall_max_rev:,.2f} → Network ${overall_net_rev:,.2f} ({overall_rev_delta:+.1f}%)\n"
        summary_msg += f"📈 Impressions: {overall_max_imps:,} → {overall_net_imps:,} ({overall_imp_delta:+.1f}%)"
        
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": summary_msg}
        })
        
        blocks.append({"type": "divider"})
        
        # Per-network summary (sorted by revenue delta)
        sorted_networks = sorted(
            network_totals.items(),
            key=lambda x: abs((x[1]['network_revenue'] - x[1]['max_revenue']) / x[1]['max_revenue'] * 100) if x[1]['max_revenue'] > 0 else 0,
            reverse=True
        )
        
        network_lines = []
        for network_name, totals in sorted_networks:
            max_rev = totals['max_revenue']
            net_rev = totals['network_revenue']
            max_imps = totals['max_impressions']
            net_imps = totals['network_impressions']
            num_dates = len(totals['dates'])
            filtered_count = len(totals['filtered_rows'])
            total_count = len(totals['rows'])
            
            rev_delta = ((net_rev - max_rev) / max_rev * 100) if max_rev > 0 else 0
            imp_delta = ((net_imps - max_imps) / max_imps * 100) if max_imps > 0 else 0
            
            # Get icon
            icon = '📡'
            network_enum = NetworkName.from_api_name(network_name)
            if network_enum:
                icon = network_enum.icon
            else:
                icon = self.NETWORK_ICONS.get(network_name.upper().replace(' ', '_'), '📡')
            
            # Status indicator
            status = "🔴" if abs(rev_delta) > threshold else "🟢"
            
            # Build line
            line = f"{status} {icon} *{network_name}* ({num_dates}d"
            if filtered_count > 0:
                line += f", {filtered_count}/{total_count} threshold aştı"
            line += f")\n"
            line += f"    💰 ${max_rev:,.2f} → ${net_rev:,.2f} ({rev_delta:+.1f}%) | 📈 {max_imps:,} → {net_imps:,} ({imp_delta:+.1f}%)"
            
            network_lines.append(line)
        
        # Add networks in chunks to avoid message length limits
        network_text = "\n".join(network_lines)
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*📡 Network Özeti ({len(network_totals)} network):*\n{network_text}"}
        })
        
        # Add failed networks warning at the end
        if failed_networks:
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🚨 *UYARI: {len(failed_networks)} network'ten veri alınamadı!*\n" +
                            f"Eksik: *{', '.join(failed_networks)}*\n" +
                            f"_Token expire olmuş veya API hatası olabilir. Kontrol edin._"
                }
            })
        
        payload = {"blocks": blocks}
        if self.channel:
            payload["channel"] = self.channel
        
        return self._send_to_slack(payload)

    def _aggregate_rows_for_display(self, rows: List[Dict]) -> List[Dict]:
        """
        Aggregate multi-day rows by network/app/ad_type for display.
        Combines all days into single rows with summed values.
        """
        aggregated = {}
        
        for row in rows:
            key = (row.get('network', ''), row.get('application', ''), row.get('ad_type', ''))
            
            if key not in aggregated:
                aggregated[key] = {
                    'network': row.get('network', ''),
                    'application': row.get('application', ''),
                    'ad_type': row.get('ad_type', ''),
                    'max_impressions': 0,
                    'network_impressions': 0,
                    'max_revenue': 0,
                    'network_revenue': 0,
                    'dates': []
                }
            
            aggregated[key]['max_impressions'] += row.get('max_impressions', 0)
            aggregated[key]['network_impressions'] += row.get('network_impressions', 0)
            aggregated[key]['max_revenue'] += row.get('max_revenue', 0)
            aggregated[key]['network_revenue'] += row.get('network_revenue', 0)
            if row.get('date'):
                aggregated[key]['dates'].append(row.get('date'))
        
        # Calculate deltas and eCPM for aggregated rows
        result = []
        for key, agg in aggregated.items():
            max_imps = agg['max_impressions']
            net_imps = agg['network_impressions']
            max_rev = agg['max_revenue']
            net_rev = agg['network_revenue']
            
            # Calculate eCPM (revenue per 1000 impressions)
            max_ecpm = (max_rev / max_imps * 1000) if max_imps > 0 else 0
            net_ecpm = (net_rev / net_imps * 1000) if net_imps > 0 else 0
            
            # Calculate deltas
            imp_delta = f"{((net_imps - max_imps) / max_imps * 100):+.1f}%" if max_imps > 0 else "0.0%"
            rev_delta = f"{((net_rev - max_rev) / max_rev * 100):+.1f}%" if max_rev > 0 else "0.0%"
            cpm_delta = f"{((net_ecpm - max_ecpm) / max_ecpm * 100):+.1f}%" if max_ecpm > 0 else "0.0%"
            
            result.append({
                'network': agg['network'],
                'application': agg['application'],
                'ad_type': agg['ad_type'],
                'max_impressions': max_imps,
                'network_impressions': net_imps,
                'imp_delta': imp_delta,
                'max_revenue': max_rev,
                'network_revenue': net_rev,
                'rev_delta': rev_delta,
                'max_ecpm': max_ecpm,
                'network_ecpm': net_ecpm,
                'cpm_delta': cpm_delta,
                'num_days': len(set(agg['dates']))
            })
        
        # Sort by network, application, ad_type
        result.sort(key=lambda x: (x['network'], x['application'], x['ad_type']))
        
        return result

    def _calculate_totals_from_rows(self, comparison_rows: List[Dict]) -> Dict:
        """Calculate totals from comparison rows."""
        return {
            'max_revenue': sum(r.get('max_revenue', 0) for r in comparison_rows),
            'network_revenue': sum(r.get('network_revenue', 0) for r in comparison_rows),
            'max_impressions': sum(r.get('max_impressions', 0) for r in comparison_rows),
            'network_impressions': sum(r.get('network_impressions', 0) for r in comparison_rows),
        }

    def _build_all_normal_blocks(
        self, totals: Dict, end_date: datetime, now_utc: datetime,
        threshold: float, min_revenue: float, total_rows: int,
        checked_rows: int, low_revenue_rows: int, failed_networks: List[str]
    ) -> List[Dict]:
        """Build Slack blocks for 'all normal' message."""
        blocks = []
        
        # Use warning header if there are failed networks
        if failed_networks:
            header_text = "⚠️ Network Comparison Report - Eksik Veri"
        else:
            header_text = "✅ Network Comparison Report - All Normal"
        
        blocks.append({
            "type": "header",
            "text": {"type": "plain_text", "text": header_text, "emoji": True}
        })
        
        blocks.append({
            "type": "context",
            "elements": [{
                "type": "mrkdwn",
                "text": f"📅 *Report Date:* {end_date.strftime('%Y-%m-%d')} | 📅 *Generated:* {now_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC"
            }]
        })
        
        blocks.append({"type": "divider"})
        
        # Calculate overall totals
        overall_max_rev = totals.get('max_revenue', 0)
        overall_net_rev = totals.get('network_revenue', 0)
        overall_rev_delta = ((overall_net_rev - overall_max_rev) / overall_max_rev * 100) if overall_max_rev > 0 else 0
        
        # Build status message
        status_msg = f"✅ *Tüm network'ler normal*\n\n"
        status_msg += f"Revenue delta threshold: *±{threshold}%*\n"
        if low_revenue_rows > 0:
            status_msg += f"Toplam {checked_rows} satır kontrol edildi ({low_revenue_rows} satır <${min_revenue:.0f} revenue), hiçbiri threshold'u aşmadı.\n\n"
        else:
            status_msg += f"Toplam {total_rows} satır kontrol edildi, hiçbiri threshold'u aşmadı.\n\n"
        status_msg += f"💰 *Toplam:* MAX ${overall_max_rev:,.2f} → Network ${overall_net_rev:,.2f} ({overall_rev_delta:+.1f}%)"
        
        # Add warning for failed networks
        if failed_networks:
            status_msg += f"\n\n⚠️ *Eksik Network'ler:* {', '.join(failed_networks)}"
            status_msg += f"\n_Bu network'lerden veri çekilemedi. Token/API sorunu olabilir._"
        
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": status_msg}
        })
        
        # If there are failed networks, add a separate warning block
        if failed_networks:
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🚨 *UYARI: {len(failed_networks)} network'ten veri alınamadı!*\n" +
                            f"Eksik: *{', '.join(failed_networks)}*\n" +
                            f"_Token expire olmuş veya API hatası olabilir. Kontrol edin._"
                }
            })
        
        return blocks
    
    def _build_threshold_exceeded_blocks(
        self, comparison_rows: List[Dict], filtered_rows: List[Dict],
        totals: Dict, end_date: datetime, now_utc: datetime,
        threshold: float, min_revenue: float, total_rows: int,
        checked_rows: int, low_revenue_rows: int, filtered_count: int,
        failed_networks: List[str], network_data: Dict[str, Any],
        network_key_resolver: Callable[[str], Optional[str]]
    ) -> List[Dict]:
        """Build Slack blocks for 'threshold exceeded' message."""
        blocks = []
        
        # Check if multi-day data (aggregate by network/app/ad_type)
        original_rows = comparison_rows.copy()
        dates = sorted(set(row.get('date', '') for row in original_rows if row.get('date')))
        is_multi_day = len(dates) > 1
        
        # Aggregate rows by network/app/ad_type if multi-day
        if is_multi_day:
            filtered_rows = self._aggregate_rows_for_display(filtered_rows)
            comparison_rows = self._aggregate_rows_for_display(comparison_rows)
        
        # Group filtered rows by network
        networks = {}
        for row in filtered_rows:
            network_name = row['network']
            if network_name not in networks:
                networks[network_name] = []
            networks[network_name].append(row)
        
        # Count affected networks
        affected_networks = len(networks)
        total_networks = len(set(r['network'] for r in comparison_rows))
        
        # Header with alert
        blocks.append({
            "type": "header",
            "text": {"type": "plain_text", "text": "⚠️ Network Comparison Report - Threshold Aşıldı", "emoji": True}
        })
        
        # Context with summary - show date range for multi-day
        if is_multi_day:
            date_range_str = f"{dates[0]} → {dates[-1]} ({len(dates)} gün)"
            context_msg = f"📅 *Date Range:* {date_range_str} | 📅 *Generated:* {now_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC | "
        else:
            context_msg = f"📅 *Report Date:* {end_date.strftime('%Y-%m-%d')} | 📅 *Generated:* {now_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC | "
        
        if low_revenue_rows > 0:
            context_msg += f"⚠️ *{filtered_count}/{checked_rows}* satır threshold (±{threshold}%) aştı ({low_revenue_rows} satır <${min_revenue:.0f} revenue) | "
        else:
            context_msg += f"⚠️ *{filtered_count}/{total_rows}* satır threshold (±{threshold}%) aştı | "
        context_msg += f"📡 *{affected_networks}/{total_networks}* network etkilendi"
        
        # Add failed networks warning to context
        if failed_networks:
            context_msg += f" | 🚨 *Eksik:* {', '.join(failed_networks)}"
        
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": context_msg}]
        })
        
        blocks.append({"type": "divider"})
        
        # Create separate block for each network (only affected networks)
        for network_name, rows in networks.items():
            # Calculate network totals (from ALL rows, not just filtered)
            all_network_rows = [r for r in comparison_rows if r['network'] == network_name]
            network_max_rev = sum(r['max_revenue'] for r in all_network_rows)
            network_net_rev = sum(r['network_revenue'] for r in all_network_rows)
            network_max_imps = sum(r['max_impressions'] for r in all_network_rows)
            network_net_imps = sum(r['network_impressions'] for r in all_network_rows)
            
            rev_delta = ((network_net_rev - network_max_rev) / network_max_rev * 100) if network_max_rev > 0 else 0
            imp_delta = ((network_net_imps - network_max_imps) / network_max_imps * 100) if network_max_imps > 0 else 0
            
            # Get network icon - try enum first, then fallback to dict
            icon = '📡'
            network_enum = NetworkName.from_api_name(network_name)
            if network_enum:
                icon = network_enum.icon
            else:
                icon = self.NETWORK_ICONS.get(network_name.upper().replace(' ', '_'), '📡')
            
            # Get network date range from network_data
            network_date_label = ""
            if network_data and network_key_resolver:
                network_key = network_key_resolver(network_name)
                if network_key and network_key in network_data:
                    net_date_range = network_data[network_key].get('date_range', {})
                    net_end = net_date_range.get('end', '')
                    if net_end:
                        if network_key == 'meta':
                            network_date_label = f" (📅 {net_end}, T-3)"
                        else:
                            network_date_label = f" (📅 {net_end})"
            
            # Network section header
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{icon} *{network_name}*{network_date_label} ({len(rows)}/{len(all_network_rows)} satır threshold aştı)\n💰 MAX: ${network_max_rev:,.2f} → Network: ${network_net_rev:,.2f} ({rev_delta:+.1f}%)\n📈 Imps: {network_max_imps:,} → {network_net_imps:,} ({imp_delta:+.1f}%)"
                }
            })
            
            # Build table for this network (only filtered rows)
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
                "elements": [{
                    "type": "rich_text_preformatted",
                    "elements": [{"type": "text", "text": table_text}]
                }]
            })
            
            blocks.append({"type": "divider"})
        
        # Add failed networks warning at the end
        if failed_networks:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🚨 *UYARI: {len(failed_networks)} network'ten veri alınamadı!*\n" +
                            f"Eksik: *{', '.join(failed_networks)}*\n" +
                            f"_Token expire olmuş veya API hatası olabilir. Kontrol edin._"
                }
            })
            blocks.append({"type": "divider"})
        
        return blocks
    
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
                "text": f"🕐 *Generated:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
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
