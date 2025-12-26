"""
Slack notifier for sending alerts.
"""
import requests
import json
from typing import Dict, List, Any
from datetime import datetime


class SlackNotifier:
    """Notifier for sending alerts to Slack."""
    
    def __init__(self, webhook_url: str, channel: str = None):
        """
        Initialize Slack notifier.
        
        Args:
            webhook_url: Slack webhook URL
            channel: Optional channel to post to (overrides webhook default)
        """
        self.webhook_url = webhook_url
        self.channel = channel
    
    def send_discrepancy_alert(self, comparisons: List[Dict[str, Any]]) -> bool:
        """
        Send discrepancy alert to Slack.
        
        Args:
            comparisons: List of comparison results
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        # Filter only comparisons with discrepancies
        discrepancies = [comp for comp in comparisons if comp['has_discrepancy']]
        
        if not discrepancies:
            return True  # No discrepancies, nothing to send
        
        # Build message
        message = self._build_message(discrepancies)
        
        # Send to Slack
        return self._send_to_slack(message)
    
    def _build_message(self, discrepancies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build Slack message payload with table format using markdown code block.
        Shows data breakdown by ad type (Banner, Interstitial, Rewarded).
        
        Args:
            discrepancies: List of comparisons with discrepancies
            
        Returns:
            Slack message payload
        """
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "⚠️ Network Data Discrepancy Alert",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Date Range:* {discrepancies[0]['date_range']['start']} to {discrepancies[0]['date_range']['end']}\n*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
            },
            {
                "type": "divider"
            }
        ]
        
        # Build table for each comparison
        for comp in discrepancies:
            network1 = comp['network1']
            network2 = comp['network2']
            
            # Get network data with ad_data breakdown
            data1 = comp.get('network1_data', {})
            data2 = comp.get('network2_data', {})
            
            ad_data1 = data1.get('ad_data', {})
            ad_data2 = data2.get('ad_data', {})
            
            # Ad type labels
            ad_types = [
                ('banner', 'Banner'),
                ('interstitial', 'Interstitial'),
                ('rewarded', 'Rewarded')
            ]
            
            # Build table header
            table = f"```\n"
            table += f"{'Ad Type':<14} {'Revenue':>12} {'Impr.':>10} {'eCPM':>8} │ {'Revenue':>12} {'Impr.':>10} {'eCPM':>8}\n"
            table += f"{'':14} {network1:>32} │ {network2:>32}\n"
            table += f"{'-'*14} {'-'*12} {'-'*10} {'-'*8} + {'-'*12} {'-'*10} {'-'*8}\n"
            
            # Add rows for each ad type
            for ad_key, ad_label in ad_types:
                # Get data for each network
                ad1 = ad_data1.get(ad_key, {'revenue': 0, 'impressions': 0, 'ecpm': 0})
                ad2 = ad_data2.get(ad_key, {'revenue': 0, 'impressions': 0, 'ecpm': 0})
                
                rev1 = f"${ad1['revenue']:,.2f}"
                imp1 = f"{int(ad1['impressions']):,}"
                ecpm1 = f"${ad1['ecpm']:.2f}"
                
                rev2 = f"${ad2['revenue']:,.2f}"
                imp2 = f"{int(ad2['impressions']):,}"
                ecpm2 = f"${ad2['ecpm']:.2f}"
                
                table += f"{ad_label:<14} {rev1:>12} {imp1:>10} {ecpm1:>8} │ {rev2:>12} {imp2:>10} {ecpm2:>8}\n"
            
            # Add separator and totals
            table += f"{'-'*14} {'-'*12} {'-'*10} {'-'*8} + {'-'*12} {'-'*10} {'-'*8}\n"
            
            # Total row
            total_rev1 = f"${data1.get('revenue', 0):,.2f}"
            total_imp1 = f"{int(data1.get('impressions', 0)):,}"
            total_ecpm1 = f"${data1.get('ecpm', 0):.2f}"
            
            total_rev2 = f"${data2.get('revenue', 0):,.2f}"
            total_imp2 = f"{int(data2.get('impressions', 0)):,}"
            total_ecpm2 = f"${data2.get('ecpm', 0):.2f}"
            
            table += f"{'TOTAL':<14} {total_rev1:>12} {total_imp1:>10} {total_ecpm1:>8} │ {total_rev2:>12} {total_imp2:>10} {total_ecpm2:>8}\n"
            table += f"```"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{network1} vs {network2}*\n{table}"
                }
            })
            
            # Add difference summary
            diff_text = "*Farklar:* "
            for disc in comp['discrepancies']:
                if disc['over_threshold']:
                    metric = disc['metric'].upper()
                    diff_pct = disc['difference_percentage']
                    if diff_pct == float('inf'):
                        diff_text += f"`{metric}: ∞%` "
                    else:
                        diff_text += f"`{metric}: {diff_pct:.1f}%` "
            
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": diff_text
                    }
                ]
            })
            
            blocks.append({
                "type": "divider"
            })
        
        payload = {
            "blocks": blocks
        }
        
        if self.channel:
            payload["channel"] = self.channel
        
        return payload
    
    def _format_value(self, value: float, metric: str) -> str:
        """
        Format value based on metric type.
        
        Args:
            value: Value to format
            metric: Metric name
            
        Returns:
            Formatted string
        """
        if metric == 'revenue':
            return f"${value:,.2f}"
        elif metric == 'ecpm':
            return f"${value:.2f}"
        else:
            return f"{int(value):,}"
    
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
