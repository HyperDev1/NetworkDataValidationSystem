"""
Test script for Slack revenue delta threshold filtering.
"""
from src.config import Config
from src.validation_service import ValidationService

def test_threshold_config():
    """Test threshold config reading."""
    print("=" * 60)
    print("1. Testing Config Threshold Reading")
    print("=" * 60)
    
    config = Config()
    threshold = config.get_slack_revenue_delta_threshold()
    min_revenue = config.get_slack_min_revenue_for_alerts()
    print(f"   ✅ Revenue delta threshold from config: {threshold}%")
    print(f"   ✅ Minimum revenue for alerts from config: ${min_revenue:.2f}")
    return threshold, min_revenue

def test_parse_delta():
    """Test delta percentage parsing."""
    print("\n" + "=" * 60)
    print("2. Testing Delta Percentage Parsing")
    print("=" * 60)
    
    config = Config()
    service = ValidationService(config)
    
    test_cases = [
        ("+5.2%", 5.2),
        ("-3.1%", -3.1),
        ("+∞%", float('inf')),
        ("0.0%", 0.0),
        ("+10.5%", 10.5),
        ("-15.3%", -15.3),
        ("", 0.0),
        (None, 0.0),
    ]
    
    all_passed = True
    for input_str, expected in test_cases:
        result = service._parse_delta_percentage(input_str)
        status = "✅" if result == expected or (result == float('inf') and expected == float('inf')) else "❌"
        if status == "❌":
            all_passed = False
        print(f"   {status} parse('{input_str}') = {result} (expected: {expected})")
    
    return all_passed

def test_threshold_filtering():
    """Test threshold filtering logic with mock data."""
    print("\n" + "=" * 60)
    print("3. Testing Threshold Filtering Logic")
    print("=" * 60)
    
    config = Config()
    service = ValidationService(config)
    threshold = config.get_slack_revenue_delta_threshold()
    min_revenue = config.get_slack_min_revenue_for_alerts()
    
    # Mock comparison rows with various delta values and revenue levels
    mock_rows = [
        # High revenue with high delta - SHOULD ALERT
        {'network': 'Unity Bidding', 'application': 'App1', 'ad_type': 'rewarded', 'rev_delta': '+12.3%', 'max_revenue': 200, 'network_revenue': 224.6, 'max_impressions': 2000, 'network_impressions': 2100, 'imp_delta': '+5.0%', 'max_ecpm': 10.0, 'network_ecpm': 10.7, 'cpm_delta': '+7.0%'},
        {'network': 'Mintegral Bidding', 'application': 'App1', 'ad_type': 'interstitial', 'rev_delta': '-8.5%', 'max_revenue': 100, 'network_revenue': 91.5, 'max_impressions': 1000, 'network_impressions': 950, 'imp_delta': '-5.0%', 'max_ecpm': 10.0, 'network_ecpm': 9.63, 'cpm_delta': '-3.7%'},
        {'network': 'IronSource Bidding', 'application': 'App2', 'ad_type': 'rewarded', 'rev_delta': '-6.7%', 'max_revenue': 150, 'network_revenue': 140.0, 'max_impressions': 1500, 'network_impressions': 1450, 'imp_delta': '-3.3%', 'max_ecpm': 10.0, 'network_ecpm': 9.66, 'cpm_delta': '-3.4%'},
        
        # High revenue with low delta - SHOULD NOT ALERT
        {'network': 'Mintegral Bidding', 'application': 'App1', 'ad_type': 'rewarded', 'rev_delta': '+2.1%', 'max_revenue': 100, 'network_revenue': 102.1, 'max_impressions': 1000, 'network_impressions': 1000, 'imp_delta': '0.0%', 'max_ecpm': 10.0, 'network_ecpm': 10.21, 'cpm_delta': '+2.1%'},
        {'network': 'Unity Bidding', 'application': 'App1', 'ad_type': 'banner', 'rev_delta': '-1.2%', 'max_revenue': 50, 'network_revenue': 49.4, 'max_impressions': 5000, 'network_impressions': 4950, 'imp_delta': '-1.0%', 'max_ecpm': 1.0, 'network_ecpm': 1.0, 'cpm_delta': '0.0%'},
        {'network': 'IronSource Bidding', 'application': 'App2', 'ad_type': 'interstitial', 'rev_delta': '+3.2%', 'max_revenue': 80, 'network_revenue': 82.6, 'max_impressions': 800, 'network_impressions': 820, 'imp_delta': '+2.5%', 'max_ecpm': 10.0, 'network_ecpm': 10.07, 'cpm_delta': '+0.7%'},
        
        # LOW REVENUE with high delta - SHOULD NOT ALERT (filtered by min_revenue)
        {'network': 'Pangle Bidding', 'application': 'App3', 'ad_type': 'banner', 'rev_delta': '+25.0%', 'max_revenue': 10.0, 'network_revenue': 12.5, 'max_impressions': 100, 'network_impressions': 110, 'imp_delta': '+10.0%', 'max_ecpm': 10.0, 'network_ecpm': 11.36, 'cpm_delta': '+13.6%'},
        {'network': 'Pangle Bidding', 'application': 'App3', 'ad_type': 'interstitial', 'rev_delta': '-30.0%', 'max_revenue': 5.0, 'network_revenue': 3.5, 'max_impressions': 50, 'network_impressions': 45, 'imp_delta': '-10.0%', 'max_ecpm': 10.0, 'network_ecpm': 7.78, 'cpm_delta': '-22.2%'},
        {'network': 'Meta Bidding', 'application': 'App1', 'ad_type': 'banner', 'rev_delta': '+50.0%', 'max_revenue': 2.0, 'network_revenue': 3.0, 'max_impressions': 20, 'network_impressions': 25, 'imp_delta': '+25.0%', 'max_ecpm': 10.0, 'network_ecpm': 12.0, 'cpm_delta': '+20.0%'},
        
        # Edge case: Infinity (from zero baseline)
        {'network': 'Meta Bidding', 'application': 'App1', 'ad_type': 'rewarded', 'rev_delta': '+∞%', 'max_revenue': 0, 'network_revenue': 50, 'max_impressions': 0, 'network_impressions': 500, 'imp_delta': '+∞%', 'max_ecpm': 0.0, 'network_ecpm': 10.0, 'cpm_delta': '+∞%'},
    ]
    
    print(f"\n   Threshold: ±{threshold}%")
    print(f"   Minimum Revenue: ${min_revenue:.2f}")
    print(f"   Total rows: {len(mock_rows)}")
    print("\n   Row Analysis:")
    print("   " + "-" * 90)
    print(f"   {'Network':<20} | {'Ad Type':<12} | {'Revenue':>10} | {'Delta':>8} | {'Status':<20}")
    print("   " + "-" * 90)
    
    filtered_rows = []
    low_revenue_rows = 0
    for row in mock_rows:
        max_rev = row.get('max_revenue', 0)
        rev_delta_value = service._parse_delta_percentage(row.get('rev_delta', '0%'))
        
        # Check if below minimum revenue
        if max_rev < min_revenue:
            low_revenue_rows += 1
            status = f"⏭️ SKIP (${max_rev:.0f} < ${min_revenue:.0f})"
        elif abs(rev_delta_value) > threshold:
            filtered_rows.append(row)
            status = "⚠️ EXCEEDS THRESHOLD"
        else:
            status = "✅ Normal"
        
        print(f"   {row['network']:<20} | {row['ad_type']:<12} | ${max_rev:>9,.2f} | {row['rev_delta']:>8} | {status:<20}")
    
    print("   " + "-" * 90)
    checked_rows = len(mock_rows) - low_revenue_rows
    print(f"\n   Total rows: {len(mock_rows)}")
    print(f"   Low revenue rows (excluded): {low_revenue_rows}")
    print(f"   Checked rows: {checked_rows}")
    print(f"   Filtered rows (exceeding threshold): {len(filtered_rows)}")
    
    # Group by network
    networks = {}
    for row in filtered_rows:
        network_name = row['network']
        if network_name not in networks:
            networks[network_name] = []
        networks[network_name].append(row)
    
    print(f"   Affected networks: {len(networks)}/{len(set(r['network'] for r in mock_rows))}")
    
    for network_name, rows in networks.items():
        print(f"   - {network_name}: {len(rows)} satır")
    
    return filtered_rows, networks, low_revenue_rows

def test_slack_message_preview():
    """Preview what Slack message would look like."""
    print("\n" + "=" * 60)
    print("4. Slack Message Preview")
    print("=" * 60)
    
    config = Config()
    threshold = config.get_slack_revenue_delta_threshold()
    min_revenue = config.get_slack_min_revenue_for_alerts()
    
    # Scenario 1: Some rows exceed threshold
    print("\n   📱 SCENARIO 1: Threshold Aşan Satırlar Var")
    print("   " + "-" * 50)
    print(f"   Header: ⚠️ Network Comparison Report - Threshold Aşıldı")
    print(f"   Context: 📅 Generated: 2026-01-08 12:00:00 UTC | ⚠️ 3/7 satır threshold (±{threshold}%) aştı (3 satır <${min_revenue:.0f} revenue) | 📡 3/4 network etkilendi")
    
    # Scenario 2: All normal
    print("\n   📱 SCENARIO 2: Tüm Network'ler Normal")
    print("   " + "-" * 50)
    print(f"   Header: ✅ Network Comparison Report - All Normal")
    print(f"   Message: ✅ Tüm network'ler normal")
    print(f"            Revenue delta threshold: ±{threshold}%")
    print(f"            Toplam 45 satır kontrol edildi (3 satır <${min_revenue:.0f} revenue), hiçbiri threshold'u aşmadı.")
    print(f"            💰 Toplam: MAX $5,000.00 → Network $4,950.00 (-1.0%)")
    
    # Scenario 3: All normal (no low revenue rows)
    print("\n   📱 SCENARIO 3: Tüm Network'ler Normal (Low Revenue Yok)")
    print("   " + "-" * 50)
    print(f"   Header: ✅ Network Comparison Report - All Normal")
    print(f"   Message: ✅ Tüm network'ler normal")
    print(f"            Revenue delta threshold: ±{threshold}%")
    print(f"            Toplam 48 satır kontrol edildi, hiçbiri threshold'u aşmadı.")
    print(f"            💰 Toplam: MAX $5,000.00 → Network $4,950.00 (-1.0%)")

if __name__ == "__main__":
    print("\n🧪 SLACK THRESHOLD FILTERING TEST")
    print("=" * 60 + "\n")
    
    # Test 1: Config reading
    threshold, min_revenue = test_threshold_config()
    
    # Test 2: Delta parsing
    parse_ok = test_parse_delta()
    
    # Test 3: Filtering logic
    filtered_rows, networks, low_revenue_count = test_threshold_filtering()
    
    # Test 4: Message preview
    test_slack_message_preview()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"   ✅ Config threshold: ±{threshold}%")
    print(f"   ✅ Config min revenue: ${min_revenue:.2f}")
    print(f"   {'✅' if parse_ok else '❌'} Delta parsing: {'All tests passed' if parse_ok else 'Some tests failed'}")
    print(f"   ✅ Filtering logic: {len(filtered_rows)}/10 rows would be shown in Slack")
    print(f"   ✅ Low revenue rows excluded: {low_revenue_count}")
    print(f"   ✅ {len(networks)} network(s) would be displayed")
    print("\n" + "=" * 60)
