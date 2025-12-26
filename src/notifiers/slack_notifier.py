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
        Build Slack message payload.
        
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
        
        # Add details for each discrepancy
        for comp in discrepancies:
            network1 = comp['network1']
            network2 = comp['network2']
            
            # Build discrepancy details
            details_text = f"*Comparing:* {network1} vs {network2}\n\n"
            
            for disc in comp['discrepancies']:
                if disc['over_threshold']:
                    metric_name = disc['metric'].capitalize()
                    val1 = self._format_value(disc['network1_value'], disc['metric'])
                    val2 = self._format_value(disc['network2_value'], disc['metric'])
                    diff = self._format_value(disc['difference'], disc['metric'])
                    diff_pct = disc['difference_percentage']
                    
                    # Handle infinity percentage
                    if diff_pct == float('inf'):
                        diff_pct_str = "∞"
                    else:
                        diff_pct_str = f"{diff_pct}%"
                    
                    details_text += f"• *{metric_name}*:\n"
                    details_text += f"  - {network1}: {val1}\n"
                    details_text += f"  - {network2}: {val2}\n"
                    details_text += f"  - Difference: {diff} ({diff_pct_str})\n\n"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": details_text
                }
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
