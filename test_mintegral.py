"""Test Mintegral API directly."""
import sys
import traceback
import requests
import hashlib
import time
from datetime import datetime, timedelta, timezone

def make_request(skey, secret, app_ids, start_date, end_date, ad_format=None):
    """Make a request to Mintegral API."""
    timestamp = int(time.time())
    time_md5 = hashlib.md5(str(timestamp).encode()).hexdigest()
    sign = hashlib.md5((secret + time_md5).encode()).hexdigest()
    
    params = {
        "skey": skey,
        "sign": sign,
        "time": timestamp,
        "start": start_date.strftime("%Y%m%d"),
        "end": end_date.strftime("%Y%m%d"),
        "group_by": "platform",
        "timezone": 0,
        "app_id": app_ids
    }
    
    if ad_format:
        params["ad_format"] = ad_format
    
    url = "https://api.mintegral.com/reporting/data"
    response = requests.get(url, params=params, timeout=30)
    return response.json()

try:
    print("Testing Mintegral API with ad_format filter...")
    
    skey = '2c9675292cb191e77c4b6eb43188f14a'
    secret = 'd734aeab8b9856a070e7167061296f57'
    app_ids = '343161,342771'
    
    end_date = datetime.now(timezone.utc) - timedelta(days=1)
    start_date = end_date
    print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Mintegral ad_format values from documentation
    ad_formats = {
        'rewarded_video': 'rewarded',
        'interstitial_video': 'interstitial', 
        'new_interstitial': 'interstitial',
        'sdk_banner': 'banner',
    }
    
    results = {}
    
    for mintegral_format, our_category in ad_formats.items():
        print(f"\n--- Fetching {mintegral_format} -> {our_category} ---")
        data = make_request(skey, secret, app_ids, start_date, end_date, mintegral_format)
        
        if str(data.get('code', '')).lower() == 'ok':
            lists = data.get('data', {}).get('lists', [])
            print(f"Rows: {len(lists)}")
            for row in lists:
                platform = row.get('platform', 'unknown').lower()
                revenue = row.get('est_revenue', 0)
                impression = row.get('impression', 0)
                print(f"  {platform}: ${revenue:.2f}, {impression} imp")
                
                key = f"{platform}_{our_category}"
                if key not in results:
                    results[key] = {'revenue': 0, 'impressions': 0}
                results[key]['revenue'] += revenue
                results[key]['impressions'] += impression
        else:
            print(f"Error: {data.get('code')}")
    
    print("\n=== SUMMARY ===")
    for key, val in sorted(results.items()):
        print(f"{key}: ${val['revenue']:.2f}, {val['impressions']} imp")
    
except Exception as e:
    print(f"Error: {str(e)}")
    traceback.print_exc()
