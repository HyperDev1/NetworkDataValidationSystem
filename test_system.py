#!/usr/bin/env python3
"""
Simple test script to verify core functionality.
"""
import sys
sys.path.insert(0, '.')

from datetime import datetime, timedelta
from src.validators import DataValidator
from src.notifiers import SlackNotifier


def test_data_validator():
    """Test the data validator."""
    print("Testing DataValidator...")
    
    validator = DataValidator(threshold_percentage=5.0)
    
    # Test data
    data1 = {
        'revenue': 1000.0,
        'impressions': 100000,
        'network': 'Network A',
        'date_range': {'start': '2025-12-25', 'end': '2025-12-25'}
    }
    
    data2 = {
        'revenue': 1100.0,  # 10% more
        'impressions': 102000,  # 2% more
        'network': 'Network B',
        'date_range': {'start': '2025-12-25', 'end': '2025-12-25'}
    }
    
    # Compare
    result = validator.compare_metrics(data1, data2, ['revenue', 'impressions'])
    
    print(f"  Network 1: {result['network1']}")
    print(f"  Network 2: {result['network2']}")
    print(f"  Has discrepancy: {result['has_discrepancy']}")
    
    for disc in result['discrepancies']:
        print(f"  - {disc['metric']}: {disc['difference_percentage']}% difference (threshold: {disc['over_threshold']})")
    
    assert result['has_discrepancy'] is True, "Should detect revenue discrepancy"
    assert result['discrepancies'][0]['over_threshold'] is True, "Revenue should exceed threshold"
    assert result['discrepancies'][1]['over_threshold'] is False, "Impressions should not exceed threshold"
    
    print("✅ DataValidator test passed!\n")


def test_slack_message_building():
    """Test Slack message building (without sending)."""
    print("Testing Slack message building...")
    
    notifier = SlackNotifier(webhook_url="https://example.com/webhook", channel="#test")
    
    # Test data
    discrepancies = [{
        'network1': 'Network A',
        'network2': 'Network B',
        'date_range': {'start': '2025-12-25', 'end': '2025-12-25'},
        'has_discrepancy': True,
        'discrepancies': [
            {
                'metric': 'revenue',
                'network1_value': 1000.0,
                'network2_value': 1100.0,
                'difference': 100.0,
                'difference_percentage': 10.0,
                'over_threshold': True
            },
            {
                'metric': 'impressions',
                'network1_value': 100000,
                'network2_value': 102000,
                'difference': 2000,
                'difference_percentage': 2.0,
                'over_threshold': False
            }
        ]
    }]
    
    # Build message
    message = notifier._build_message(discrepancies)
    
    assert 'blocks' in message, "Message should have blocks"
    assert len(message['blocks']) > 0, "Message should have content"
    assert message.get('channel') == '#test', "Channel should be set"
    
    print(f"  Generated {len(message['blocks'])} message blocks")
    print("✅ Slack message building test passed!\n")


def test_multiple_network_comparison():
    """Test comparing multiple networks."""
    print("Testing multiple network comparison...")
    
    validator = DataValidator(threshold_percentage=5.0)
    
    # Test data for 3 networks
    networks = [
        {
            'revenue': 1000.0,
            'impressions': 100000,
            'network': 'Network A (Baseline)',
            'date_range': {'start': '2025-12-25', 'end': '2025-12-25'}
        },
        {
            'revenue': 1020.0,  # 2% more - within threshold
            'impressions': 101000,
            'network': 'Network B',
            'date_range': {'start': '2025-12-25', 'end': '2025-12-25'}
        },
        {
            'revenue': 1200.0,  # 20% more - exceeds threshold
            'impressions': 95000,
            'network': 'Network C',
            'date_range': {'start': '2025-12-25', 'end': '2025-12-25'}
        }
    ]
    
    # Compare
    results = validator.compare_multiple_networks(networks, ['revenue', 'impressions'])
    
    assert len(results) == 2, "Should compare baseline with 2 other networks"
    assert results[0]['has_discrepancy'] is False, "Network B should be within threshold"
    assert results[1]['has_discrepancy'] is True, "Network C should exceed threshold"
    
    has_any = validator.has_any_discrepancy(results)
    assert has_any is True, "Should detect at least one discrepancy"
    
    print(f"  Compared {len(networks)} networks")
    print(f"  Found discrepancies: {has_any}")
    print("✅ Multiple network comparison test passed!\n")


def test_zero_baseline_handling():
    """Test handling of zero baseline values."""
    print("Testing zero baseline handling...")
    
    validator = DataValidator(threshold_percentage=5.0)
    
    # Test data with zero baseline
    data1 = {
        'revenue': 0.0,  # Zero baseline
        'impressions': 0,
        'network': 'Network A',
        'date_range': {'start': '2025-12-25', 'end': '2025-12-25'}
    }
    
    data2 = {
        'revenue': 100.0,  # Non-zero value
        'impressions': 1000,
        'network': 'Network B',
        'date_range': {'start': '2025-12-25', 'end': '2025-12-25'}
    }
    
    # Compare
    result = validator.compare_metrics(data1, data2, ['revenue', 'impressions'])
    
    # Should detect discrepancy when baseline is 0 and comparison is non-zero
    assert result['has_discrepancy'] is True, "Should detect discrepancy with zero baseline"
    assert result['discrepancies'][0]['difference_percentage'] == float('inf'), "Should be infinity for zero baseline"
    assert result['discrepancies'][0]['over_threshold'] is True, "Should exceed threshold"
    
    # Test case where both are zero (no discrepancy)
    data3 = {
        'revenue': 0.0,
        'impressions': 0,
        'network': 'Network C',
        'date_range': {'start': '2025-12-25', 'end': '2025-12-25'}
    }
    
    result2 = validator.compare_metrics(data1, data3, ['revenue', 'impressions'])
    assert result2['has_discrepancy'] is False, "Should not detect discrepancy when both are zero"
    
    print("  Zero baseline handling works correctly")
    print("✅ Zero baseline handling test passed!\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Running Network Data Validation System Tests")
    print("=" * 60 + "\n")
    
    try:
        test_data_validator()
        test_slack_message_building()
        test_multiple_network_comparison()
        test_zero_baseline_handling()
        
        print("=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
